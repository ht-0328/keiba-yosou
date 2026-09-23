"""買い目1つ。"""

from __future__ import annotations

from dataclasses import dataclass

from .ticket_type import TicketType


@dataclass(frozen=True)
class Ticket:
    """券種と馬番の組。順不同の券種（馬連・ワイド・3連複）は馬番を昇順にそろえ、同じ組が1つになるようにする。

    ``combo`` は払戻・オッズの表の馬番/組番と同じ形（馬番を2桁ずつ並べた文字列。馬連 ``0204``、3連単 ``040203``）。
    """

    ticket_type: TicketType
    horses: tuple[int, ...]

    def __post_init__(self) -> None:
        spec = self.ticket_type.spec
        if len(self.horses) != spec.horse_count:
            raise ValueError(f"{self.ticket_type.label}の買い目は {spec.horse_count}頭です: {self.horses}")
        if len(set(self.horses)) != len(self.horses):
            raise ValueError(f"同じ馬が2回入っています: {self.horses}")
        if not spec.is_ordered:
            object.__setattr__(self, "horses", tuple(sorted(self.horses)))

    @property
    def combo(self) -> str:
        return "".join(f"{horse:02d}" for horse in self.horses)
