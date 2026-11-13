"""予算に収まるフォーメーションのうち、見積もりの払戻の合計がいちばん大きいものを選ぶ。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from yosou.shared.dataset import HORSE_NO

from ..payout import PayoutPool
from .formation import Formation
from .formation_choice import FormationChoice
from .formation_value import FormationValue
from .leg_ordering import LegOrdering


class FormationSearch:
    """設計書 06 の図3。各レースの馬を ``LegOrdering`` の順に並べ、頭数の並び（各レース何頭）のうち点数が予算以下のものを全部試し、
    各レースは並べた順に上から選んで、見積もりの払戻の合計がいちばん大きいフォーメーションを選ぶ。

    各レースの上位 k 頭の組は、上位 k−1 頭の組を含むので、予算の上限まで並べた全部の組の値（``ComboGrid``）を1回だけ出し、
    5つの向きに累積の和をとって、どの頭数の並びの合計も引くだけで分かるようにする（計算を使い回す）。
    """

    def __init__(self, ordering: LegOrdering, value: FormationValue) -> None:
        self._ordering = ordering
        self._value = value

    @property
    def ordering(self) -> LegOrdering:
        return self._ordering

    def best(self, legs: Sequence[pd.DataFrame], budget: int, pool: PayoutPool) -> FormationChoice:
        """予算 ``budget`` 点でのいちばん良いフォーメーション。"""
        return self.best_by_budget(legs, [budget], pool)[budget]

    def best_by_budget(self, legs: Sequence[pd.DataFrame], budgets: Sequence[int], pool: PayoutPool) -> dict[int, FormationChoice]:
        """予算ごとのいちばん良いフォーメーション。``legs`` は5レースの確率の表（``RaceWinShare`` の結果。全頭）。"""
        if min(budgets) < 1:
            raise ValueError(f"予算は 1点以上にしてください: {min(budgets)}")
        top = max(budgets)
        ordered = [self._ordering.order(leg).head(min(len(leg), top)) for leg in legs]
        grid = self._value.grid(ordered, pool)
        payout_sums = self._cumulative(grid.expected_payout)
        probability_sums = self._cumulative(grid.probability)
        points = self._points([len(leg) for leg in ordered])
        return {budget: self._choice(ordered, budget, points, payout_sums, probability_sums) for budget in budgets}

    def _choice(self, ordered: Sequence[pd.DataFrame], budget: int, points: np.ndarray, payout_sums: np.ndarray,
                probability_sums: np.ndarray) -> FormationChoice:
        """点数が予算以下の頭数の並びのうち、見積もりの払戻の合計がいちばん大きいもの。"""
        allowed = np.where(points <= budget, payout_sums, -np.inf)
        position = np.unravel_index(int(np.argmax(allowed)), allowed.shape)
        sizes = [int(index) + 1 for index in position]
        formation = Formation(tuple(tuple(int(number) for number in leg[HORSE_NO].head(size))
                                    for leg, size in zip(ordered, sizes, strict=True)))
        return FormationChoice(formation, float(probability_sums[position]), float(payout_sums[position]))

    def _cumulative(self, values: np.ndarray) -> np.ndarray:
        """5つの向きに累積の和をとる。``[k1-1, …, k5-1]`` が各レースの上位 k 頭のフォーメーションの合計になる。"""
        result = values
        for axis in range(values.ndim):
            result = np.cumsum(result, axis=axis)
        return result

    def _points(self, field_sizes: Sequence[int]) -> np.ndarray:
        """頭数の並びごとの点数（各レースの頭数のかけ算）。"""
        result = np.ones(field_sizes, dtype=np.int64)
        for axis, size in enumerate(field_sizes):
            shape = [1] * len(field_sizes)
            shape[axis] = size
            result = result * np.arange(1, size + 1, dtype=np.int64).reshape(shape)
        return result
