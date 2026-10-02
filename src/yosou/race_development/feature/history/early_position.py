"""序盤の位置と、その区分。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .relative_rank import RelativeRank

#: 先団・中団の線（序盤の位置がこの値以下なら、その区分。設計書 10 の 3）。
FRONT_LIMIT = 1 / 3
MIDDLE_LIMIT = 2 / 3


class EarlyPosition:
    """最初のコーナーでの順位と出走頭数から、序盤の位置（0〜1）と区分（先団 0・中団 1・後方 2）を出す（設計書 10 の 3）。

    **序盤の位置の物差しの、ただ1つの置き場所。** 目的変数（②）と、過去走から作る特徴量（K・L）の両方が使う。
    """

    def __init__(self) -> None:
        self._relative_rank = RelativeRank()

    def of(self, rank: pd.Series, field_size: pd.Series) -> pd.Series:
        """序盤の位置。順位が無ければ欠損値。"""
        return self._relative_rank.of(rank, field_size)

    def zone_of(self, position: pd.Series) -> pd.Series:
        """区分（0・1・2）。序盤の位置が欠損値なら欠損値。"""
        zone = np.select([position <= FRONT_LIMIT, position <= MIDDLE_LIMIT], [0.0, 1.0], default=2.0)
        return pd.Series(zone, index=position.index).where(position.notna())

    def is_front(self, position: pd.Series) -> pd.Series:
        """先団（3分の1まで）なら 1、そうでなければ 0。序盤の位置が欠損値なら欠損値。"""
        return (position <= FRONT_LIMIT).astype("float64").where(position.notna())
