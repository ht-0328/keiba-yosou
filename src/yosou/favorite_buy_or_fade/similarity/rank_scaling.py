"""数の列を、学習データの中の順位にそろえる。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 0〜1 に一様に散らばる値のばらつき（標準偏差 1/√12）を 1 にする倍率。
_UNIFORM_SCALE = float(np.sqrt(12.0))


class RankScaling:
    """数の列を、学習データの中の順位（0〜1）に直し、平均 0・ばらつき 1 にそろえる（設計書 12 の 3。方針の ``scaling = "順位"``）。

    値の大小の順だけを使うので、極端に大きい値（外れ値）に引きずられない。同じ値が並ぶときは、その並びの真ん中の順位にする。
    学習データのどの値より大きい値は 1、小さい値は 0 の位置になる。
    """

    def __init__(self) -> None:
        self._sorted: dict[str, np.ndarray] = {}

    def fit(self, numbers: pd.DataFrame) -> RankScaling:
        """``numbers`` は欠損値を埋めた数の列（どの行も同じ値の列は含まない）。列ごとに、値を小さい順に並べて覚える。"""
        self._sorted = {column: np.sort(numbers[column].to_numpy(dtype=float)) for column in numbers.columns}
        return self

    def transform(self, numbers: pd.DataFrame) -> pd.DataFrame:
        """列の並びは ``fit`` のときと同じ。"""
        return pd.DataFrame({column: self._positions(column, numbers[column]) for column in self._sorted},
                            index=numbers.index)

    def _positions(self, column: str, values: pd.Series) -> np.ndarray:
        """値が学習データの並びのどこに来るか（0〜1。同じ値はその並びの真ん中）を、平均 0・ばらつき 1 にしたもの。"""
        known = self._sorted[column]
        targets = values.to_numpy(dtype=float)
        lower = np.searchsorted(known, targets, side="left")
        upper = np.searchsorted(known, targets, side="right")
        return ((lower + upper) / 2 / len(known) - 0.5) * _UNIFORM_SCALE
