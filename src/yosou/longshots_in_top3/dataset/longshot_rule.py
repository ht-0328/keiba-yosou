"""穴馬の決まりを表す値。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from yosou.shared.dataset import LARGE_FIELD_FROM
from yosou.shared.feature import as_numbers

from .longshot_zone import LongshotZone


@dataclass(frozen=True)
class LongshotRule:
    """穴馬の決まり（設計書 08 の 3）。頭数ごとの「穴馬の最初の人気」と「大穴の最初の人気」を持つ。

    13頭以下（少頭数）なら 4番人気以下、14頭以上（多頭数）なら 6番人気以下を穴馬とする。
    危険な人気馬の予想の「人気馬」（1〜3番、1〜5番人気）の、ちょうど裏返しである。
    穴馬のうち、13頭以下は 6番人気まで、14頭以上は 9番人気までが中穴で、それより下が大穴。
    多頭数とみなす頭数（``LARGE_FIELD_FROM``）は、人気馬の予想と同じ値を共通から使う。
    """

    #: 少頭数・多頭数それぞれの、穴馬の最初の人気（この人気を含める）。人気馬の範囲の次の人気。
    FIRST_LONGSHOT_IN_SMALL_FIELD = 4
    FIRST_LONGSHOT_IN_LARGE_FIELD = 6
    #: 少頭数・多頭数それぞれの、大穴の最初の人気（この人気を含める）。その手前までが中穴。
    FIRST_BIG_IN_SMALL_FIELD = 7
    FIRST_BIG_IN_LARGE_FIELD = 10

    def popularity_range(self, field_size: int) -> tuple[int, int]:
        """その頭数での、穴馬にする人気の範囲（いちばん上, いちばん下）。どちらも含む。いちばん下は最下位。"""
        first, _ = self._firsts(field_size)
        return first, field_size

    def is_longshot(self, popularity: float | None, field_size: int) -> bool:
        """その人気・その頭数なら穴馬か。人気が欠損値なら（人気が分からないので）穴馬にしない。"""
        if popularity is None or pd.isna(popularity):
            return False
        first, _ = self._firsts(field_size)
        return float(popularity) >= first

    def zone_of(self, popularity: float | None, field_size: int) -> LongshotZone | None:
        """その人気・その頭数での区分。穴馬でなければ（人気馬か、人気が分からなければ）None。"""
        if not self.is_longshot(popularity, field_size):
            return None
        _, first_big = self._firsts(field_size)
        return LongshotZone.BIG if float(popularity) >= first_big else LongshotZone.MID

    def are_longshots(self, popularity: pd.Series, field_size: pd.Series) -> pd.Series:
        """出走の行ごとに穴馬かを答える（まとめて判定する形）。人気が欠損値の行は ``False``。"""
        first, _ = self._firsts_of(field_size)
        return as_numbers(popularity) >= first

    def zones_of(self, popularity: pd.Series, field_size: pd.Series) -> pd.Series:
        """出走の行ごとの区分の名前（中穴・大穴）。穴馬でない行は None。"""
        ranks = as_numbers(popularity)
        first, first_big = self._firsts_of(field_size)
        labels = np.select(
            [ranks >= first_big, ranks >= first], [LongshotZone.BIG.label, LongshotZone.MID.label], default=None,
        )
        return pd.Series(labels, index=popularity.index, dtype=object)

    def _firsts(self, field_size: int) -> tuple[int, int]:
        """その頭数での（穴馬の最初の人気, 大穴の最初の人気）。"""
        if field_size >= LARGE_FIELD_FROM:
            return self.FIRST_LONGSHOT_IN_LARGE_FIELD, self.FIRST_BIG_IN_LARGE_FIELD
        return self.FIRST_LONGSHOT_IN_SMALL_FIELD, self.FIRST_BIG_IN_SMALL_FIELD

    def _firsts_of(self, field_size: pd.Series) -> tuple[np.ndarray, np.ndarray]:
        """出走の行ごとの（穴馬の最初の人気, 大穴の最初の人気）。"""
        is_large = (as_numbers(field_size) >= LARGE_FIELD_FROM).to_numpy()
        first = np.where(is_large, self.FIRST_LONGSHOT_IN_LARGE_FIELD, self.FIRST_LONGSHOT_IN_SMALL_FIELD)
        first_big = np.where(is_large, self.FIRST_BIG_IN_LARGE_FIELD, self.FIRST_BIG_IN_SMALL_FIELD)
        return first, first_big
