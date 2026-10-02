"""「芝ダート × 距離」から、モデルを分ける単位を決める。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd

#: 特徴量の表の、芝ダと距離の列の名前（まとまり A）。
SURFACE = "芝ダ"
DISTANCE = "距離"


@dataclass(frozen=True)
class CourseUnitMap:
    """芝ダ → その芝ダで単位にする距離の並び（設計書 08 の 3）。

    学習データで1番人気が ``min_rows`` 頭以上いる距離を、そのまま単位にする。少ない距離は、同じ芝ダの
    いちばん近い単位の距離とまとめる（差が同じなら長いほう）。ある芝ダでどの距離も少なければ、
    いちばん頭数の多い距離を単位にして、その芝ダを1つにまとめる。
    単位の名前は「芝2000m」のように、芝ダと単位の距離をつなげたもの。
    """

    distances: Mapping[str, tuple[int, ...]]

    @classmethod
    def from_rows(cls, features: pd.DataFrame, min_rows: int) -> CourseUnitMap:
        """学習データの特徴量（芝ダと距離の列）から作る。"""
        counts = features.groupby([SURFACE, DISTANCE], observed=True).size()
        return cls({str(surface): cls._unit_distances(count, min_rows)
                    for surface, count in counts.groupby(level=0)})

    @staticmethod
    def _unit_distances(counts: pd.Series, min_rows: int) -> tuple[int, ...]:
        """1つの芝ダの、単位にする距離。少なければ、いちばん頭数の多い距離1つ。"""
        by_distance = counts.droplevel(0)
        enough = by_distance[by_distance >= min_rows]
        if enough.empty:
            return (int(by_distance.idxmax()),)
        return tuple(sorted(int(distance) for distance in enough.index))

    def unit_of(self, surface: str, distance: float) -> str:
        """その芝ダ・距離の単位の名前。学習データに無い芝ダなら ``ValueError``。"""
        if surface not in self.distances:
            raise ValueError(f"学習データに無い芝ダです: {surface}")
        nearest = min(self.distances[surface], key=lambda unit: (abs(unit - distance), -unit))
        return f"{surface}{nearest}m"

    def units_of(self, features: pd.DataFrame) -> pd.Series:
        """行ごとの単位の名前。行の並びと index は ``features`` と同じ。"""
        pairs = zip(features[SURFACE], features[DISTANCE])
        return pd.Series([self.unit_of(str(surface), float(distance)) for surface, distance in pairs],
                         index=features.index, name="単位", dtype=object)

    def members(self, features: pd.DataFrame) -> dict[str, list[int]]:
        """単位の名前 → その単位に入る距離（学習データにあるもの）。報告の表に使う。"""
        pairs = features[[SURFACE, DISTANCE]].drop_duplicates()
        units = self.units_of(pairs)
        return {unit: sorted(int(d) for d in pairs.loc[units == unit, DISTANCE]) for unit in sorted(set(units))}
