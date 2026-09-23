"""低配当目を削る。"""

from __future__ import annotations

from collections.abc import Sequence

from ..ticket import Ticket
from .odds_book import OddsBook


class OddsFloorCut:
    """確定オッズが下限未満の買い目を落とす（ルール集 SRF-04・SRT-05）。

    そのレース・券種のオッズが無ければ判定できないので None を返す（呼ぶ側は見送りにする）。
    組番のオッズだけが無い買い目（無投票など）は、削らずに残す。
    """

    def __init__(self, odds_book: OddsBook) -> None:
        self._odds_book = odds_book

    def apply(self, race_id: str, tickets: Sequence[Ticket], floor: float) -> list[Ticket] | None:
        if not tickets:
            return []
        if not self._odds_book.has_race(race_id, tickets[0].ticket_type):
            return None
        return [ticket for ticket in tickets if self._is_kept(race_id, ticket, floor)]

    def _is_kept(self, race_id: str, ticket: Ticket, floor: float) -> bool:
        odds = self._odds_book.odds_of(race_id, ticket)
        return odds is None or odds >= floor
