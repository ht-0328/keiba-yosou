"""組の表の各行が、型の買い目に入るかを判定する。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.betting import TicketType

from .formation import DOUBLE_AXIS, Formation

#: 組の表の、馬ごとの位置の列（``HorseSlots`` の位置。枠連は枠の中でいちばん小さい位置）。
POSITIONS: tuple[str, ...] = ("pos1", "pos2", "pos3")
#: 券種の形。単 = 1頭、順不同2 = 馬連・ワイド・枠連、順序2 = 馬単、順不同3 = 3連複、順序3 = 3連単。
SINGLE, PAIR, ORDERED_PAIR, TRIPLE, ORDERED_TRIPLE = "単", "順不同2", "順序2", "順不同3", "順序3"
SHAPES: dict[str, str] = {
    TicketType.WIN.label: SINGLE, TicketType.PLACE.label: SINGLE,
    TicketType.QUINELLA.label: PAIR, TicketType.WIDE.label: PAIR, "枠連": PAIR,
    TicketType.EXACTA.label: ORDERED_PAIR, TicketType.TRIO.label: TRIPLE, TicketType.TRIFECTA.label: ORDERED_TRIPLE,
}


class FormationMask:
    """組の表（列 ``pos1``・``pos2``・``pos3``。無い列は使わない）の各行が、型 ``formation`` の買い目に入るかの真偽を出す（docs/01 の 4）。

    位置 p が「p ≤ 軸の上限」なら軸（K）、「p ≤ 相手の上限」なら軸か相手（A）。消は位置が欠損値なので、どちらにも入らない。
    相手を確率の線で決める型では、相手の上限はレースごとに「線以上の馬の数」（組の表の列 ``n50``・``n25``。``HorseSlots.partner_counts``）と軸の上限の大きいほう。
    ただし、線以上の馬が券種の馬の数に足りないレースでも全レースを買えるように、確率の順に券種の馬の数までは必ず相手にする（docs/01 の 2）。
    - 単: 1頭目が K。
    - 順不同2（馬連・ワイド・枠連）: どちらかが K で、両方が A。
    - 順序2（馬単）: 1頭目が K で、2頭目が A。
    - 順不同3（3連複）: 流し = どれかが K で全部が A。2列目も軸 = 2頭以上が K で全部が A。
    - 順序3（3連単）: 流し = 1頭目が K で 2・3頭目が A。2列目も軸 = 1・2頭目が K で 3頭目が A。
    """

    def __init__(self, shape: str) -> None:
        if shape not in (SINGLE, PAIR, ORDERED_PAIR, TRIPLE, ORDERED_TRIPLE):
            raise ValueError(f"知らない券種の形です: {shape}")
        self._shape = shape
        self._horse_count = {SINGLE: 1, PAIR: 2, ORDERED_PAIR: 2, TRIPLE: 3, ORDERED_TRIPLE: 3}[shape]

    @classmethod
    def of(cls, ticket_label: str) -> FormationMask:
        return cls(SHAPES[ticket_label])

    def _partner_limit(self, combos: pd.DataFrame, formation: Formation) -> float | np.ndarray:
        if not formation.by_threshold:
            return formation.partner_limit
        counts = combos[formation.threshold_column].to_numpy(dtype=float)
        # 線以上の馬が券種の馬の数に足りないレースでも全レースを買うため、確率の順に券種の馬の数まで（位置 馬の数 − 1 まで）は相手にする
        least = float(self._horse_count - 1)
        return np.maximum(np.maximum(formation.axis_limit, counts), least)

    def of_rows(self, combos: pd.DataFrame, formation: Formation) -> np.ndarray:
        count = self._horse_count
        positions = [combos[column].to_numpy(dtype=float) for column in POSITIONS[:count]]
        in_axis = [position <= formation.axis_limit for position in positions]
        limit = self._partner_limit(combos, formation)
        in_all = [position <= limit for position in positions]
        everyone = np.logical_and.reduce(in_all)
        if self._shape == SINGLE:
            return in_axis[0]
        if self._shape == PAIR:
            return (in_axis[0] | in_axis[1]) & everyone
        if self._shape == ORDERED_PAIR:
            return in_axis[0] & in_all[1]
        double = formation.second_column == DOUBLE_AXIS
        if self._shape == TRIPLE:
            axes = np.sum(in_axis, axis=0)
            return (axes >= (2 if double else 1)) & everyone
        return in_axis[0] & (in_axis[1] if double else in_all[1]) & in_all[2]
