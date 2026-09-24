"""1つの区切りで、買い方を確かめる。"""

from __future__ import annotations

from collections.abc import Collection, Mapping

import numpy as np
import pandas as pd

from yosou.shared.dataset import TOP3
from yosou.shared.dataset.column_names import POPULARITY
from yosou.shared.place_value import PlacePriceEstimator

from 馬券の買い方の検証.analysis.ticket import TicketType

from ..combined import HorseTableBuilder, RaceProbabilityBuilder, RaceProbabilityFit
from ..combined.horse_columns import WIN_PROBABILITY
from ..horse_roles import DANGER, HorseValues, RoleAssigner
from ..market import CombinationTable
from ..walk_forward import PART, PART_TEST, PART_VALID, WINDOW
from ..windows import TestWindow
from .betting_plan_chooser import BettingPlanChooser, TicketChoice
from .candidate_columns import COMBO, RACE, TICKET
from .payout_table import PAYOUT
from .race_columns import UPSET
from .race_table_builder import RaceTableBuilder
from .probability_calibrator import ProbabilityCalibrator
from .race_candidate_pricer import RaceCandidatePricer
from .ticket_set_builder import TicketSetBuilder
from .race_upset_probability import RaceUpsetProbability
from .window_result import WindowResult

#: 消にする1番人気: 検証期間の1番人気の人気馬の危険度のうち、上位この割合（本当に危険なものだけ）。
EXCLUDE_TOP_SHARE = 0.1
#: 2頭軸にする、2番目の馬の3着以内の確率の線（かなりの自信があるとき）。
SECOND_AXIS_LINE = 0.5
#: 荒れそうとする: 検証期間のレースの荒れそうな確率のうち、上位この割合。
UPSET_TOP_SHARE = 0.3


class WindowBacktest:
    """1つの区切りで、買い方を確かめる。

    1. 検証期間とテスト期間の1頭ごとの表を作り、検証期間で勝率の出し方を決めて、両方の期間の勝率を出す。
    2. 馬ごとの期待値を出し、役割（消・軸・◎）を付ける（``HorseValues``・``RoleAssigner``）。消の線は、検証期間の
       1番人気の危険度の上位 ``EXCLUDE_TOP_SHARE``。
    3. レースごとの荒れそうな確率を出す（``RaceUpsetProbability``）。検証期間の上位 ``UPSET_TOP_SHARE`` を「荒れそう」とする。
    4. 券種ごとの買い目の候補を作り、当たる確率・オッズ・期待値を付ける（``RaceCandidatePricer``）。
    5. 当たる確率のずれを、検証期間の券種 × オッズの帯ごとの比で直す（``ProbabilityCalibrator``）。
    6. 期待値の低い買い目を切り、点数を絞り、賭け金・券種全体の期待値・合成オッズ・払戻を付ける（``TicketSetBuilder``）。
    7. 検証期間（1つ前の区切りの検証の半年と、この区切りの検証の半年 = 1年）で、券種ごとの線と1開催日のレース数を決める。
    8. テスト期間で、決めたとおりに買う。テスト期間の結果は、どの手順にも使わない。
    """

    def __init__(self, horse_builder: HorseTableBuilder, probability_builder: RaceProbabilityBuilder,
                 chooser: BettingPlanChooser) -> None:
        self._horse_builder = horse_builder
        self._probability_builder = probability_builder
        self._chooser = chooser

    def run(self, window: TestWindow, tables: Mapping[TicketType, CombinationTable], payouts: pd.DataFrame,
            prices: Mapping[TicketType, PlacePriceEstimator], graded: Collection[str],
            previous: WindowResult | None = None) -> WindowResult:
        horses = self._horse_builder.build(window)
        valid, test = horses[horses[PART] == PART_VALID], horses[horses[PART] == PART_TEST]
        fit = self._probability_builder.fit(valid)
        values = HorseValues(prices[TicketType.PLACE])
        valid, test = values.build(self._with_win(valid, fit)), values.build(self._with_win(test, fit))
        exclude_line = self._top_share_line(valid.loc[valid[POPULARITY] == 1, DANGER], EXCLUDE_TOP_SHARE)
        assigner = RoleAssigner(exclude_line, SECOND_AXIS_LINE)
        valid, test = assigner.assign(valid), assigner.assign(test)
        upset = RaceUpsetProbability(tables[TicketType.TRIO], fit.order_probability())
        valid_upset, test_upset = upset.of(valid), upset.of(test)
        upset_line = self._top_share_line(valid_upset, UPSET_TOP_SHARE)
        valid_races = RaceTableBuilder().build(valid, graded, valid_upset, upset_line)
        test_races = RaceTableBuilder().build(test, graded, test_upset, upset_line)
        pricer = RaceCandidatePricer(tables, prices, fit.order_probability())
        valid_upset_ids, test_upset_ids = self._upset_ids(valid_races), self._upset_ids(test_races)
        valid_candidates = self._with_payouts(pricer.build(valid, valid_upset_ids), payouts)
        test_candidates = self._with_payouts(pricer.build(test, test_upset_ids), payouts)
        history_candidates = self._joined(previous.valid_candidates if previous else None, valid_candidates)
        calibrator = ProbabilityCalibrator.learn(history_candidates)
        sets = TicketSetBuilder()
        valid_tickets = sets.build(calibrator.apply(valid_candidates), valid_upset_ids)
        test_candidates = calibrator.apply(test_candidates)
        test_tickets = sets.build(test_candidates, test_upset_ids)
        history = self._joined(previous.valid_tickets if previous else None, valid_tickets)
        history_races = self._joined(previous.valid_races if previous else None, valid_races)
        plan, choices = self._chooser.choose(history, history_races)
        return WindowResult(
            bought=plan.apply(test_tickets, test_races).assign(**{WINDOW: window.name}),
            reference=plan.with_all_tickets().apply(test_tickets, test_races).assign(**{WINDOW: window.name}),
            choices=[self._record(window, choice) for choice in choices],
            fit={WINDOW: window.name, **fit.summary(), "1開催日のレース数": plan.races_per_day or "全部",
                 "消の線（1番人気の危険度）": exclude_line, "荒れそうの線": upset_line,
                 "検証期間": "1年" if previous is not None else "半年"},
            candidates=test_candidates.assign(**{WINDOW: window.name}), races=test_races.assign(**{WINDOW: window.name}),
            valid_candidates=valid_candidates, valid_tickets=valid_tickets, valid_races=valid_races,
        )

    def _record(self, window: TestWindow, choice: TicketChoice) -> dict[str, object]:
        """券種ごとの、検証期間で選んだ線とその成績（表に出す形）。"""
        return {
            WINDOW: window.name, TICKET: choice.ticket, "券種全体の期待値の線": choice.line, "検証のレース数": choice.races,
            "検証の点数": choice.points, "検証の的中数": choice.hits, "検証の投資（円）": choice.stake,
            "検証の払戻（円）": choice.payout, "検証の回収率": choice.rate, "検証の控えめな見積もり": choice.conservative,
            "テストで買うか": "買う" if choice.adopted else "買わない",
        }

    def _with_win(self, horses: pd.DataFrame, fit: RaceProbabilityFit) -> pd.DataFrame:
        return horses.assign(**{WIN_PROBABILITY: fit.win_probability(horses)})

    def _top_share_line(self, values: pd.Series, share: float) -> float:
        """``values`` の上位 ``share`` の境目（それ以上が上位）。値が無ければ無限大（どれも当てはまらない）。"""
        known = values.dropna()
        return float(np.quantile(known, 1.0 - share)) if len(known) else float("inf")

    def _upset_ids(self, races: pd.DataFrame) -> set[str]:
        return set(races.loc[races[UPSET], RACE])

    def _with_payouts(self, candidates: pd.DataFrame, payouts: pd.DataFrame) -> pd.DataFrame:
        merged = candidates.merge(payouts, on=[RACE, TICKET, COMBO], how="left")
        return merged.assign(**{PAYOUT: merged[PAYOUT].fillna(0.0)})

    def _joined(self, earlier: pd.DataFrame | None, later: pd.DataFrame) -> pd.DataFrame:
        """検証期間の表: 1つ前の区切りの検証の半年があれば、前に足して1年にする。"""
        if earlier is None:
            return later
        return pd.concat([earlier[list(later.columns)], later], ignore_index=True)
