"""探索: 格子の全戦略を評価して並べる。"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from .adoption_rule import AdoptionRule
from .strategy import Strategy
from .strategy_evaluator import StrategyEvaluator
from .strategy_grid import StrategyGrid
from .strategy_result import StrategyResult


class SearchRunner:
    """探索期間のレースで格子の全戦略を評価し、回収率の高い順に並べ、採否の基準で候補を選ぶ。"""

    def __init__(self, evaluator: StrategyEvaluator, grid: StrategyGrid, rule: AdoptionRule,
                 progress: Callable[[int, int], None] | None = None) -> None:
        self._evaluator = evaluator
        self._grid = grid
        self._rule = rule
        self._progress = progress or (lambda done, total: None)

    def run(self, search_races: pd.DataFrame) -> list[StrategyResult]:
        strategies = self._grid.strategies(search_races)
        results: list[StrategyResult] = []
        for index, strategy in enumerate(strategies, start=1):
            results.append(self._evaluator.evaluate(strategy, search_races))
            self._progress(index, len(strategies))
        return sorted(results, key=self._sort_key)

    def adopted(self, results: list[StrategyResult]) -> list[StrategyResult]:
        """採否の基準を満たす戦略（回収率の順）。"""
        return [result for result in results if self._rule.is_adopted(result.total)]

    def chosen(self, results: list[StrategyResult], limit: int) -> list[Strategy]:
        """確認期間で確かめる戦略（候補の上位 ``limit``）。"""
        return [result.strategy for result in self.adopted(results)[:limit]]

    def _sort_key(self, result: StrategyResult) -> tuple[bool, float]:
        rate = result.total.return_rate
        return (rate is None, -(rate or 0.0))
