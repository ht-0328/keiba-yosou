"""組み合わせの券種の決まりごと（払戻の表・組の馬の数・着順を区別するか）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TicketKind:
    """1つの券種。``ordered`` が真なら着順どおりの組（馬単・3連単）、偽なら順不同の組（馬連・ワイド・3連複）。"""

    name: str
    payout_table: str
    horses: int
    ordered: bool

    def canonical(self, combo: tuple[int, ...]) -> tuple[int, ...]:
        """買い目と払戻の組を同じ形にする。順不同の券種は馬番の小さい順に並べる。"""
        return combo if self.ordered else tuple(sorted(combo))


#: 使える券種。名前はルール集の書き方（馬連・馬単・ワイド・3連複・3連単）。
TICKET_KINDS: dict[str, TicketKind] = {
    kind.name: kind for kind in (
        TicketKind("馬連", "hr__馬連払戻", 2, False),
        TicketKind("馬単", "hr__馬単払戻", 2, True),
        TicketKind("ワイド", "hr__ワイド払戻", 2, False),
        TicketKind("3連複", "hr__3連複払戻", 3, False),
        TicketKind("3連単", "hr__3連単払戻", 3, True),
    )
}


def ticket_kind(name: str) -> TicketKind:
    """名前から券種を引く。無い名前は、選べる名前を添えて落とす。"""
    try:
        return TICKET_KINDS[name.strip()]
    except KeyError:
        raise LookupError(f"知らない券種です: {name}\n選べるもの: {', '.join(TICKET_KINDS)}") from None
