"""確定オッズの帳簿。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from ..repository.final_odds_repository import COMBO, ODDS
from ..ticket import Ticket, TicketType

_RACE_ID = "race_id"


class OddsBook:
    """(レースID, 券種, 組番) → 確定オッズ の帳簿。複勝・ワイドは最低オッズ。

    ``odds`` は券種 → ``FinalOddsRepository.read`` の表。オッズの無い券種・レースは引けない（``has_race`` で確かめる）。
    """

    def __init__(self, odds: Mapping[TicketType, pd.DataFrame]) -> None:
        self._odds: dict[tuple[str, TicketType, str], float] = {}
        self._races: set[tuple[str, TicketType]] = set()
        for ticket_type, table in odds.items():
            self._add(ticket_type, table)

    def _add(self, ticket_type: TicketType, table: pd.DataFrame) -> None:
        for race_id, combo, value in zip(table[_RACE_ID], table[COMBO], table[ODDS]):
            self._odds[(str(race_id), ticket_type, str(combo))] = float(value)
            self._races.add((str(race_id), ticket_type))

    def odds_of(self, race_id: str, ticket: Ticket) -> float | None:
        """その買い目の確定オッズ。無ければ None。"""
        return self._odds.get((race_id, ticket.ticket_type, ticket.combo))

    def has_race(self, race_id: str, ticket_type: TicketType) -> bool:
        """そのレース・券種のオッズがあるか。"""
        return (race_id, ticket_type) in self._races
