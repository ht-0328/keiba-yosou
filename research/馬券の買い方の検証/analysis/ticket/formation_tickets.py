"""列ごとの馬番の並びから買い目を作る。"""

from __future__ import annotations

import itertools
from collections.abc import Sequence

from .ticket import Ticket
from .ticket_type import TicketType


class FormationTickets:
    """フォーメーション（列ごとに候補の馬番を置く）から、買い目の並びを作る純粋な計算。

    列をまたぐ全部の組み合わせのうち、同じ馬が2回入るものを除き、順不同の券種では同じ組を1つにする。
    ボックスは、同じ馬番の並びを頭数ぶんの列に置いたものとして同じ計算で作れる。
    """

    def build(self, ticket_type: TicketType, columns: Sequence[Sequence[int]]) -> list[Ticket]:
        if len(columns) != ticket_type.spec.horse_count:
            raise ValueError(f"{ticket_type.label}の列は {ticket_type.spec.horse_count}つです: {len(columns)}列")
        distinct = (horses for horses in itertools.product(*columns) if len(set(horses)) == len(horses))
        tickets: dict[Ticket, None] = {}
        for horses in distinct:
            tickets.setdefault(Ticket(ticket_type, tuple(horses)), None)
        return list(tickets)

    def box(self, ticket_type: TicketType, horses: Sequence[int]) -> list[Ticket]:
        """ボックス（選んだ馬の全組み合わせ）。"""
        return self.build(ticket_type, [list(horses)] * ticket_type.spec.horse_count)
