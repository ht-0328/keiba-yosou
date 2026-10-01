"""数の列を標準化する。"""

from __future__ import annotations

import pandas as pd


class StandardScaling:
    """数の列を、平均 0・標準偏差 1 にそろえる（設計書 12 の 3。方針の ``scaling = "標準化"``）。

    平均と標準偏差は、``fit`` に渡した学習データ（1つの単位の1番人気全員）から求め、学習・評価・予測で同じ値を使う。
    """

    def __init__(self) -> None:
        self._means = pd.Series(dtype=float)
        self._spreads = pd.Series(dtype=float)

    def fit(self, numbers: pd.DataFrame) -> StandardScaling:
        """``numbers`` は欠損値を埋めた数の列（どの行も同じ値の列は含まない）。"""
        self._means, self._spreads = numbers.mean(), numbers.std(ddof=0)
        return self

    def transform(self, numbers: pd.DataFrame) -> pd.DataFrame:
        """列の並びは ``fit`` のときと同じ。"""
        return (numbers - self._means) / self._spreads
