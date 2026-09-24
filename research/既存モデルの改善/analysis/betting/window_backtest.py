"""1つの区切りで、印の買い方を確かめる。"""

from __future__ import annotations

from collections.abc import Collection, Mapping

import pandas as pd

from yosou.favorites_out_of_top3.danger import DangerThreshold
from yosou.shared.dataset import TOP3
from yosou.shared.place_value import PlacePriceEstimator

from 馬券の買い方の検証.analysis.ticket import TicketType

from ..combined import HorseTableBuilder, RaceProbabilityBuilder, RaceProbabilityFit
from ..combined.horse_columns import WIN_PROBABILITY
from ..market import CombinationTable
from ..marks.mark_assigner import MarkAssigner
from ..marks.mark_material import DANGER, MarkMaterial
from ..walk_forward import PART, PART_TEST, PART_VALID, WINDOW
from ..windows import TestWindow
from .candidate_columns import COMBO, RACE, TICKET
from .mark_candidate_builder import MarkCandidateBuilder
from .mark_plan_chooser import MarkPlanChooser, TicketChoice
from .payout_table import PAYOUT
from .race_table_builder import RaceTableBuilder
from .window_result import WindowResult


class WindowBacktest:
    """1つの区切りで、印の買い方を確かめる。

    1. 検証期間とテスト期間の1頭ごとの表を作り、検証期間で勝率の出し方を決めて、両方の期間の勝率を出す。
    2. 消の線（人気馬の危険度）を検証期間で決め、両方の期間の馬に印を付ける（``MarkAssigner``）。
    3. 印のルールで買い目を作り、当たる確率・期待値・払戻を付ける（``MarkCandidateBuilder``）。
    4. 検証期間（この区切りの検証の半年と、前の区切りのテストの半年 = 1年）で、勝負するレース・押さえ・
       券種ごとの期待値の線を決める（``MarkPlanChooser``）。
    5. テスト期間で、決めたとおりに買う。テスト期間の結果は、どの手順にも使わない。
    """

    def __init__(self, horse_builder: HorseTableBuilder, probability_builder: RaceProbabilityBuilder,
                 chooser: MarkPlanChooser) -> None:
        self._horse_builder = horse_builder
        self._probability_builder = probability_builder
        self._chooser = chooser

    def run(self, window: TestWindow, tables: Mapping[TicketType, CombinationTable], payouts: pd.DataFrame,
            prices: Mapping[TicketType, PlacePriceEstimator], graded: Collection[str],
            previous: WindowResult | None = None) -> WindowResult:
        horses = self._horse_builder.build(window)
        valid, test = horses[horses[PART] == PART_VALID], horses[horses[PART] == PART_TEST]
        fit = self._probability_builder.fit(valid)
        material = MarkMaterial(prices[TicketType.PLACE])
        valid, test = material.build(self._with_win(valid, fit)), material.build(self._with_win(test, fit))
        exclude_line = self._exclude_line(valid)
        assigner = MarkAssigner(exclude_line)
        valid, test = assigner.assign(valid), assigner.assign(test)
        builder = MarkCandidateBuilder(tables, prices, fit.order_probability())
        valid_candidates = self._with_payouts(builder.build(valid), payouts)
        test_candidates = self._with_payouts(builder.build(test), payouts)
        valid_races = RaceTableBuilder().build(valid, valid_candidates, graded)
        test_races = RaceTableBuilder().build(test, test_candidates, graded)
        history, history_races = self._validation(valid_candidates, valid_races, previous)
        plan, choices = self._chooser.choose(history, history_races)
        return WindowResult(
            bought=plan.apply(test_candidates, test_races).assign(**{WINDOW: window.name}),
            reference=plan.with_all_tickets().apply(test_candidates, test_races).assign(**{WINDOW: window.name}),
            choices=[self._record(window, choice, plan.describe()) for choice in choices],
            fit={WINDOW: window.name, **fit.summary(), "1開催日のレース数": plan.races_per_day,
                 "◎が危ういの線": plan.shaky_line, "消の線": exclude_line,
                 "検証期間": "1年" if previous is not None else "半年"},
            candidates=test_candidates.assign(**{WINDOW: window.name}), races=test_races.assign(**{WINDOW: window.name}),
        )

    def _record(self, window: TestWindow, choice: TicketChoice, plan: str) -> dict[str, object]:
        """券種ごとの、検証期間で選んだ線とその成績（表に出す形）。"""
        return {
            WINDOW: window.name, TICKET: choice.ticket, "勝負するレースと押さえ": plan, "期待値の線": choice.line,
            "検証の点数": choice.points, "検証のレース数": choice.races, "検証の的中数": choice.hits,
            "検証の回収率": choice.rate, "検証の控えめな見積もり": choice.conservative,
            "テストで買うか": "買う" if choice.adopted else "買わない",
        }

    def _with_win(self, horses: pd.DataFrame, fit: RaceProbabilityFit) -> pd.DataFrame:
        return horses.assign(**{WIN_PROBABILITY: fit.win_probability(horses)})

    def _exclude_line(self, valid: pd.DataFrame) -> float:
        """消の線: 人気馬の危険度の線を、検証期間の人気馬の実際の4着以下で決める（``DangerThreshold``）。"""
        favorites = valid[valid[DANGER].notna() & valid[TOP3].notna()]
        if favorites.empty:
            return float("nan")
        return DangerThreshold().choose(favorites[DANGER], 1 - favorites[TOP3].astype(int))

    def _with_payouts(self, candidates: pd.DataFrame, payouts: pd.DataFrame) -> pd.DataFrame:
        merged = candidates.merge(payouts, on=[RACE, TICKET, COMBO], how="left")
        return merged.assign(**{PAYOUT: merged[PAYOUT].fillna(0.0)})

    def _validation(self, candidates: pd.DataFrame, races: pd.DataFrame,
                    previous: WindowResult | None) -> tuple[pd.DataFrame, pd.DataFrame]:
        """検証期間の買い目とレース。前の区切りがあれば、そのテストの半年を足して1年にする。"""
        if previous is None:
            return candidates, races
        return (pd.concat([previous.candidates[list(candidates.columns)], candidates], ignore_index=True),
                pd.concat([previous.races[list(races.columns)], races], ignore_index=True))

