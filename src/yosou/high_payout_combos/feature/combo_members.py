"""組の馬ごとの材料。"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

import numpy as np

from .material_names import HORSE_MATERIALS, POP


@dataclass(frozen=True, eq=False)
class ComboMembers:
    """1つの券種の組の表の、組の馬ごとの材料（行 × 組の位置 × 材料）。

    - ``values``: 行は組、2つ目の軸は組番の並び（1頭目・2頭目・3頭目）、3つ目の軸は ``HORSE_MATERIALS`` の並び。
    - ``is_ordered``: 着順を区別する券種（馬単・3連単）か。

    材料にするときの馬の並びは、着順を区別する券種は組番の並びのまま、順不同の券種（ワイド・馬連・3連複）は
    単勝人気の小さい順（同じ人気なら組番の並び）。例: 馬連 03-07 で 7番が2番人気・3番が5番人気なら、位置 0 は 7番。
    """

    values: np.ndarray
    is_ordered: bool

    @property
    def horse_count(self) -> int:
        """組の馬の数（2 か 3）。"""
        return self.values.shape[1]

    def in_combo_order(self, name: str) -> np.ndarray:
        """材料 ``name`` の値（行 × 組の位置）。位置は組番の並び。"""
        return self.values[:, :, HORSE_MATERIALS.index(name)]

    def in_feature_order(self, name: str) -> np.ndarray:
        """材料 ``name`` の値（行 × 組の位置）。位置は材料にするときの並び。"""
        return self._feature_ordered[:, :, HORSE_MATERIALS.index(name)]

    @cached_property
    def _feature_ordered(self) -> np.ndarray:
        if self.is_ordered:
            return self.values
        by_popularity = np.argsort(self.in_combo_order(POP), axis=1, kind="stable")
        return np.take_along_axis(self.values, by_popularity[:, :, None], axis=1)
