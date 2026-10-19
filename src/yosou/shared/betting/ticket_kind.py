"""券種の名前から、券種（``TicketType`` か枠連）を引く。"""

from __future__ import annotations

from .bracket_ticket import BRACKET, BracketTicket
from .ticket_type import TicketType


def ticket_kind(text: str) -> TicketType | BracketTicket:
    """券種の名前（例 ``馬連``・``枠連``）→ 券種。``枠連`` なら ``BRACKET``、ほかは ``TicketType.parse``（知らない名前は ``ValueError``）。
    買い目の表の券種の列から、オッズ・払戻を読む部品に渡す券種を引くのに使う。"""
    return BRACKET if text.strip() == BRACKET.label else TicketType.parse(text)
