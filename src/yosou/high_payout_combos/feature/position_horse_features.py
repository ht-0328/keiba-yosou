"""組の位置ごとの馬の材料。"""

from __future__ import annotations

from itertools import product

import pandas as pd

from .combo_members import ComboMembers
from .material_names import POSITION_MATERIALS


class PositionHorseFeatures:
    """組の馬ごとの材料（``POSITION_MATERIALS`` の 20個）を、位置ごとの列にする。

    列の名前は、材料の名前の後ろに位置（0 始まり）を付ける。例: 位置 0 の馬の予想の1着の確率は ``pw0``、位置 1 の馬の単勝人気は ``pop1``。
    位置は ``ComboMembers`` の材料にするときの並び（馬単・3連単は着順、ほかは単勝人気の小さい順）。
    """

    def names(self, horse_count: int) -> tuple[str, ...]:
        """``horse_count`` 頭の組の列の名前（位置 0 の 20個、位置 1 の 20個、… の順）。"""
        return tuple(f"{material}{position}" for position, material in product(range(horse_count), POSITION_MATERIALS))

    def of(self, members: ComboMembers, index: pd.Index) -> pd.DataFrame:
        """行の並びは ``members`` と同じ。``index`` は付ける index。"""
        slots = product(range(members.horse_count), POSITION_MATERIALS)
        columns = {f"{material}{position}": members.in_feature_order(material)[:, position] for position, material in slots}
        return pd.DataFrame(columns, index=index)
