"""単位で分けないときの、単位の決め方。"""

from __future__ import annotations

import pandas as pd

from .course_unit_map import DISTANCE

#: 全部を1つにした単位の名前。
WHOLE_UNIT = "全部"


class SingleUnitMap:
    """全部を1つの単位にする単位の決め方（方針の ``[unit]`` の ``split = "なし"``。設計書 08 の 3）。

    ``CourseUnitMap`` と同じ呼び方で使える。芝ダと距離は単位にせず、特徴量として距離に入る。
    """

    def unit_of(self, surface: str, distance: float) -> str:
        """どの芝ダ・距離でも、同じ1つの単位。"""
        return WHOLE_UNIT

    def units_of(self, features: pd.DataFrame) -> pd.Series:
        """行ごとの単位の名前（全部同じ）。行の並びと index は ``features`` と同じ。"""
        return pd.Series(WHOLE_UNIT, index=features.index, name="単位", dtype=object)

    def members(self, features: pd.DataFrame) -> dict[str, list[int]]:
        """単位の名前 → その単位に入る距離（学習データにあるもの全部）。報告の表に使う。"""
        return {WHOLE_UNIT: sorted(int(distance) for distance in features[DISTANCE].dropna().unique())}
