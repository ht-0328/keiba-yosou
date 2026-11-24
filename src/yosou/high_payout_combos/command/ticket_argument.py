"""券種を絞る引数（``--ticket``）。"""

from __future__ import annotations

import argparse

from yosou.shared.betting import TicketType

from ..feature import TICKET_TYPES

#: ``--ticket`` に書ける名前の案内。
TICKET_CHOICES = " / ".join(ticket_type.label for ticket_type in TICKET_TYPES)


def add_ticket_argument(parser: argparse.ArgumentParser) -> None:
    """``--ticket`` を足す。券種の名前（ワイド・馬連・馬単・3連複・3連単）か英名（wide など）を、いくつでも書ける。"""
    parser.add_argument(
        "--ticket", nargs="*", default=None, metavar="券種",
        help=f"対象の券種: {TICKET_CHOICES}（英名 wide・quinella・exacta・trio・trifecta でもよい。省略すると5つ全部）",
    )


def ticket_types_of(args: argparse.Namespace) -> list[TicketType]:
    """``--ticket`` で渡された券種（書いた順）。渡されなければ5つ全部。この予想が扱わない券種は ``ValueError``。"""
    if not args.ticket:
        return list(TICKET_TYPES)
    return [_ticket_type(text) for text in args.ticket]


def _ticket_type(text: str) -> TicketType:
    by_name = {**{each.label: each for each in TICKET_TYPES}, **{each.key: each for each in TICKET_TYPES}}
    found = by_name.get(text.strip())
    if found is None:
        raise ValueError(f"この予想が扱わない券種です: {text}（{TICKET_CHOICES}）")
    return found
