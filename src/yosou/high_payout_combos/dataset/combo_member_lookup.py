"""組の馬の材料を、馬ごとの材料の表から引く。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.combo_value import horse_columns

from ..feature import ComboMembers
from ..feature.column_names import HORSE_NO, RACE_ID
from ..feature.material_names import HORSE_MATERIALS

#: 馬ごとの材料の表に無い馬の、行の位置の代わりの値。
_MISSING = -1


class ComboMemberLookup:
    """馬ごとの材料の表（``HorseMaterials.of``）から、組の各位置の馬の材料を引く。

    ``slots`` は組の行ごとに、各位置の馬が馬ごとの材料の表の何行目かを返す（表に無い馬は −1）。
    ``members`` は、その行の位置から ``ComboMembers``（行 × 組の位置 × 材料）を作る。
    """

    def __init__(self, materials: pd.DataFrame) -> None:
        self._values = materials[list(HORSE_MATERIALS)].to_numpy(dtype=float)
        horse_keys = pd.MultiIndex.from_arrays([materials[RACE_ID], materials[HORSE_NO].astype(np.int64)])
        self._row_of_horse = pd.Series(np.arange(len(materials)), index=horse_keys)

    def slots(self, rows: pd.DataFrame, horse_count: int) -> np.ndarray:
        """``rows`` は市場の表の行（列 ``race_id``・``h1``…）。戻り値は 行 × 組の位置の、馬ごとの材料の表の行の位置（無ければ −1）。"""
        return np.stack([self._slot(rows, name) for name in horse_columns(horse_count)], axis=1)

    def members(self, slots: np.ndarray, is_ordered: bool) -> ComboMembers:
        """``slots``（どの位置も −1 でない行だけ）の馬の材料。"""
        return ComboMembers(self._values[slots], is_ordered)

    def _slot(self, rows: pd.DataFrame, horse_column: str) -> np.ndarray:
        wanted = pd.MultiIndex.from_arrays([rows[RACE_ID], rows[horse_column].astype(np.int64)])
        return self._row_of_horse.reindex(wanted).fillna(_MISSING).to_numpy(dtype=np.int64)
