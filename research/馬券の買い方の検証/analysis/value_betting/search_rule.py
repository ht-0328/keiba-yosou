"""探索の採否の基準と、確認に回す戦略の選び方。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .protocol import SEARCH_CANDIDATE_LIMIT, SEARCH_MIN_GOOD_WINDOWS, SEARCH_MIN_POINTS, SEARCH_MIN_RETURN_RATE
from .strategy_result import StrategyResult

CANDIDATE = "候補"
NOT_CANDIDATE = ""


@dataclass(frozen=True)
class SearchAdoptionRule:
    """探索（4区切り）で戦略を候補にする基準と、確認に回す数（docs/05-round3-protocol.md。結果を見てから変えない）。

    候補 = 4区切り合計で 回収率 ``min_return_rate`` 以上・点数 ``min_points`` 以上・回収率 ``min_return_rate`` 以上の区切りが
    ``min_good_windows`` 以上。確認に回すのは、候補のうち控えめな見積もり（``ConservativeRate``）の高い順に ``candidate_limit`` まで。
    """

    min_return_rate: float = SEARCH_MIN_RETURN_RATE
    min_points: int = SEARCH_MIN_POINTS
    min_good_windows: int = SEARCH_MIN_GOOD_WINDOWS
    candidate_limit: int = SEARCH_CANDIDATE_LIMIT

    def is_candidate(self, result: StrategyResult) -> bool:
        total = result.total
        if np.isnan(total.rate) or total.rate < self.min_return_rate or total.points < self.min_points:
            return False
        return result.windows_at_or_above(self.min_return_rate) >= self.min_good_windows

    def verdict(self, result: StrategyResult) -> str:
        return CANDIDATE if self.is_candidate(result) else NOT_CANDIDATE

    def chosen(self, results: Sequence[StrategyResult]) -> list[StrategyResult]:
        """確認に回す戦略（候補を控えめな見積もりの高い順に並べ、上位 ``candidate_limit`` まで）。"""
        candidates = [result for result in results if self.is_candidate(result)]
        ranked = sorted(candidates, key=lambda result: self._conservative(result), reverse=True)
        return ranked[:self.candidate_limit]

    def describe(self) -> str:
        return (f"4区切り合計で回収率 {self.min_return_rate:.0%} 以上・{self.min_points} 点以上・"
                f"回収率 {self.min_return_rate:.0%} 以上の区切りが {self.min_good_windows} つ以上。"
                f"候補のうち控えめな見積もりの高い順に {self.candidate_limit} つまで確認に回す")

    def _conservative(self, result: StrategyResult) -> float:
        value = result.total.conservative
        return -np.inf if np.isnan(value) else float(value)
