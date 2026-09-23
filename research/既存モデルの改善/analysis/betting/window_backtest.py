"""1つの区切りで、組み合わせた買い方を確かめる。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from yosou.shared.place_value import PlacePriceEstimator

from 馬券の買い方の検証.analysis.ticket import TicketType

from ..combined import HorseTableBuilder, RaceProbabilityBuilder, RaceProbabilityFit
from ..combined.horse_columns import WIN_PROBABILITY
from ..market import CombinationTable
from ..walk_forward import PART, PART_TEST, PART_VALID, WINDOW
from ..windows import TestWindow
from .betting_rule import COMBO, RACE, TICKET
from .candidate_builder import CandidateBuilder
from .payout_table import PAYOUT
from .rule_chooser import RuleChooser
from .rule_grid import RULE_GRID
from .window_result import WindowResult


class WindowBacktest:
    """1つの区切りで、組み合わせた買い方を確かめる。

    1. 検証期間とテスト期間の1頭ごとの表を作る（3つの予想の予測を並べる）。
    2. 検証期間で、勝率の出し方（材料の重み・Stern の補正）を決め、両方の期間の勝率を出す。
    3. 両方の期間の買い目の候補（期待値つき）を作り、払戻を突き合わせる。
    4. 券種ごとに、検証期間の回収率で買い方を選ぶ。回収率が 100% 以上の券種だけ、テスト期間でその買い方で買う。
    テスト期間の結果は、どの手順にも使わない。
    """

    def __init__(self, horse_builder: HorseTableBuilder, probability_builder: RaceProbabilityBuilder,
                 chooser: RuleChooser) -> None:
        self._horse_builder = horse_builder
        self._probability_builder = probability_builder
        self._chooser = chooser

    def run(self, window: TestWindow, tables: Mapping[TicketType, CombinationTable], payouts: pd.DataFrame,
            prices: Mapping[TicketType, PlacePriceEstimator]) -> WindowResult:
        horses = self._horse_builder.build(window)
        valid, test = horses[horses[PART] == PART_VALID], horses[horses[PART] == PART_TEST]
        fit = self._probability_builder.fit(valid)
        builder = CandidateBuilder(tables, prices, fit.order_probability())
        valid_candidates = self._with_payouts(builder.build(self._with_win(valid, fit)), payouts)
        test_candidates = self._with_payouts(builder.build(self._with_win(test, fit)), payouts)
        outcomes = [self._ticket(ticket, valid_candidates, test_candidates, window) for ticket in TicketType]
        return WindowResult(
            bought=pd.concat([bought for bought, _, _ in outcomes], ignore_index=True).assign(**{WINDOW: window.name}),
            reference=pd.concat([reference for _, reference, _ in outcomes], ignore_index=True).assign(**{WINDOW: window.name}),
            choices=[record for _, _, record in outcomes],
            fit={WINDOW: window.name, **fit.summary()},
        )

    def _with_win(self, horses: pd.DataFrame, fit: RaceProbabilityFit) -> pd.DataFrame:
        return horses.assign(**{WIN_PROBABILITY: fit.win_probability(horses)})

    def _with_payouts(self, candidates: pd.DataFrame, payouts: pd.DataFrame) -> pd.DataFrame:
        merged = candidates.merge(payouts, on=[RACE, TICKET, COMBO], how="left")
        return merged.assign(**{PAYOUT: merged[PAYOUT].fillna(0.0)})

    def _ticket(self, ticket: TicketType, valid: pd.DataFrame, test: pd.DataFrame,
                window: TestWindow) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
        """1つの券種: 検証期間で買い方を選び、テスト期間に当てる（買うもの, 参考, 選んだ記録）。"""
        choice = self._chooser.choose(valid[valid[TICKET] == ticket.label], RULE_GRID[ticket])
        chosen = test[test[TICKET] == ticket.label]
        reference = choice.rule.select(chosen) if choice.rule is not None else chosen.iloc[0:0]
        bought = reference if choice.adopted else chosen.iloc[0:0]
        record = {
            WINDOW: window.name, TICKET: ticket.label,
            "選んだ買い方": choice.rule.describe() if choice.rule is not None else "（点数が足りず選べない）",
            "検証の点数": choice.points, "検証のレース数": choice.races, "検証の回収率": choice.rate,
            "テストで買うか": "買う" if choice.adopted else "買わない",
        }
        return bought, reference, record
