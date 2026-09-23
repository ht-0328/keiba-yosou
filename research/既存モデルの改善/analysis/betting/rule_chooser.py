"""検証期間の回収率で、券種ごとの買い方を決める。"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from .betting_rule import RACE, BettingRule
from .payout_table import PAYOUT
from .rule_choice import RuleChoice


class RuleChooser:
    """券種ごとに、買い方の候補（``RULE_GRID``）を検証期間の候補の買い目に当てて、回収率がいちばん高いものを選ぶ。

    点数が ``min_points`` 未満か、買ったレースが ``min_races`` 未満の買い方は選ばない（たまたまの大当たりで選ばないように）。
    選んだ買い方の検証期間の回収率が ``min_rate``（100%）未満なら、その券種はテスト期間に買わない。
    """

    def __init__(self, min_points: int = 100, min_races: int = 30, min_rate: float = 1.0) -> None:
        self._min_points = min_points
        self._min_races = min_races
        self._min_rate = min_rate

    def choose(self, candidates: pd.DataFrame, rules: Sequence[BettingRule]) -> RuleChoice:
        """``candidates`` はその券種の検証期間の候補（払戻の列を持つ）。"""
        results = [self._evaluate(rule, candidates) for rule in rules]
        eligible = [result for result in results if result.points >= self._min_points and result.races >= self._min_races]
        if not eligible:
            return RuleChoice(None, False, 0, 0, float("nan"))
        best = max(eligible, key=lambda result: result.rate)
        return RuleChoice(best.rule, best.rate >= self._min_rate, best.points, best.races, best.rate)

    def _evaluate(self, rule: BettingRule, candidates: pd.DataFrame) -> RuleChoice:
        bought = rule.select(candidates)
        points = len(bought)
        rate = float(bought[PAYOUT].sum() / (100.0 * points)) if points else float("nan")
        return RuleChoice(rule, False, points, int(bought[RACE].nunique()), rate)
