"""人気馬の決まりを表す値。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from yosou.shared.dataset import LARGE_FIELD_FROM
from yosou.shared.feature import as_numbers

#: 人気の範囲の、いちばん上の順位。
_FIRST = 1


@dataclass(frozen=True)
class FavoriteRule:
    """人気馬の決まり（設計書 08 の 3）。頭数の線引きと、頭数ごとの人気の範囲を持つ。

    13頭以下（少頭数）なら 1〜3番人気、14頭以上（多頭数）なら 1〜5番人気を人気馬とする。
    どの頭数でも、人気馬が出走馬の 2〜4割に収まるようにした線引きである。
    多頭数とみなす頭数（``LARGE_FIELD_FROM``）は、穴馬の予想と同じ値を共通から使う。
    """

    #: 少頭数・多頭数それぞれの、人気馬にする人気のいちばん下（この人気を含める）。
    LAST_FAVORITE_IN_SMALL_FIELD = 3
    LAST_FAVORITE_IN_LARGE_FIELD = 5

    def popularity_range(self, field_size: int) -> tuple[int, int]:
        """その頭数での、人気馬にする人気の範囲（いちばん上, いちばん下）。どちらも含む。"""
        if field_size >= LARGE_FIELD_FROM:
            return _FIRST, self.LAST_FAVORITE_IN_LARGE_FIELD
        return _FIRST, self.LAST_FAVORITE_IN_SMALL_FIELD

    def is_favorite(self, popularity: float | None, field_size: int) -> bool:
        """その人気・その頭数なら人気馬か。人気が欠損値なら（人気が分からないので）人気馬にしない。"""
        if popularity is None or pd.isna(popularity):
            return False
        first, last = self.popularity_range(field_size)
        return first <= float(popularity) <= last

    def are_favorites(self, popularity: pd.Series, field_size: pd.Series) -> pd.Series:
        """出走の行ごとに人気馬かを答える（まとめて判定する形）。人気が欠損値の行は ``False``。"""
        ranks = as_numbers(popularity)
        last = np.where(as_numbers(field_size) >= LARGE_FIELD_FROM,
                        self.LAST_FAVORITE_IN_LARGE_FIELD, self.LAST_FAVORITE_IN_SMALL_FIELD)
        return (ranks >= _FIRST) & (ranks <= last)
