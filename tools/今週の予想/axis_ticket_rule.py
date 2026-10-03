"""軸の1頭から印に流す買い目（3連複・3連単）のルール。"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, permutations

from yosou.shared.betting import TicketType

#: 軸の2パターン。◎軸は ◎ を軸にする。軸馬は ◎○▲ のうち3着以内の確率がいちばん高い馬（``MarkRule`` の列 ``axis``）を軸にする。
TOP_AXIS, HORSE_AXIS = "◎軸", "軸馬"
#: 軸から流す相手の印（注は表示だけの印なので入れない）。軸の馬は除くので、軸が ○ のときは ◎ が相手に回る。
PARTNER_MARKS: tuple[str, ...] = ("◎", "○", "▲", "△", "☆")


@dataclass(frozen=True)
class AxisTicketRule:
    """軸の1頭から相手（○▲△☆。軸が ○ なら ◎ も）に流す券種のルール（設計書「買うレースと買い目を決める」08 の 2）。

    - 3連複: 1頭軸流し（軸 − 相手2頭の組。相手6頭なら 15点）。
    - 3連単: 1頭軸マルチ（軸と相手2頭の並びを全部。相手6頭なら 90点）。
    ``value_line`` があれば、組の期待値（``ComboExpectedValue``）がその線以上の買い目だけにする。無ければ全点。
    ``totals`` は、この買い方を入れる合計の組（``TOP_AXIS``・``HORSE_AXIS``）。
    """

    ticket_type: TicketType
    axis: str
    value_line: float | None
    stake_units: float
    totals: tuple[str, ...]

    @property
    def label(self) -> str:
        """表に出す買い方の名前。例: ``3連単（◎軸・マルチ・期待値 1.0 以上）``。"""
        shape = "マルチ" if self.ticket_type.spec.is_ordered else "流し"
        line = f"・期待値 {self.value_line:.1f} 以上" if self.value_line is not None else ""
        return f"{self.ticket_type.label}（{self.axis}・{shape}{line}）"

    def combos(self, by_mark: dict[str, list[int]], axes: dict[str, int]) -> list[tuple[int, ...]]:
        """``axes`` はパターン → 軸の馬番。軸がいない（印が無い）レースは組まない。期待値の線はここでは見ない（``MarkTickets`` が絞る）。"""
        axis = axes.get(self.axis)
        if axis is None:
            return []
        partners = [horse for mark in PARTNER_MARKS for horse in by_mark.get(mark, []) if horse != axis]
        pairs = combinations(partners, 2)
        if self.ticket_type.spec.is_ordered:
            return sorted(order for pair in pairs for order in permutations((axis, *pair)))
        return sorted(tuple(sorted((axis, *pair))) for pair in pairs)
