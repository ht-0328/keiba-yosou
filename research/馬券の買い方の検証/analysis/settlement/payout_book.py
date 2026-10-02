"""買い目と払戻を照合する帳簿。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.repository import REFUNDED, void_column
from yosou.shared.repository.payout_repository import COMBO, YEN

from ..ticket import Ticket

_RACE_ID = "race_id"


class PayoutBook:
    """(レースID, 券種, 組番) → 払戻円 の帳簿。券種ごとの不成立（不成立か特払）と、払戻データがあるレースも答える。

    複勝・ワイドの複数行や同着は、組番ごとに別の行なので、そのまま組番で引ける（同じ組番が複数あれば合計）。
    ``payouts`` は券種 → ``PayoutRepository.read`` の表、``flags`` は ``PayoutFlagRepository.read`` の表。
    """

    def __init__(self, payouts: Mapping[TicketType, pd.DataFrame], flags: pd.DataFrame) -> None:
        self._yen: dict[tuple[str, TicketType, str], int] = {}
        for ticket_type, table in payouts.items():
            self._add(ticket_type, table)
        self._void: set[tuple[str, TicketType]] = set()
        for ticket_type in TicketType:
            self._add_void(ticket_type, flags)
        self._refunded: set[str] = set(flags[flags[REFUNDED]][_RACE_ID]) if len(flags) else set()
        self._races: set[str] = {race_id for race_id, _, _ in self._yen} | set(flags[_RACE_ID])

    def _add(self, ticket_type: TicketType, table: pd.DataFrame) -> None:
        totals = table.groupby([_RACE_ID, COMBO])[YEN].sum()
        for (race_id, combo), yen in totals.items():
            self._yen[(str(race_id), ticket_type, str(combo))] = int(yen)

    def _add_void(self, ticket_type: TicketType, flags: pd.DataFrame) -> None:
        column = void_column(ticket_type)
        if column not in flags.columns:
            return
        self._void |= {(str(race_id), ticket_type) for race_id in flags[flags[column]][_RACE_ID]}

    def payout_yen(self, race_id: str, ticket: Ticket) -> int:
        """その買い目に 100円で戻る円（外れなら 0）。"""
        return self._yen.get((race_id, ticket.ticket_type, ticket.combo), 0)

    def is_void(self, race_id: str, ticket_type: TicketType) -> bool:
        """その券種がそのレースで成立しなかった（不成立か特払）か。"""
        return (race_id, ticket_type) in self._void

    def is_refunded(self, race_id: str) -> bool:
        """そのレースに返還があったか（払戻はある。数を報告するだけ）。"""
        return race_id in self._refunded

    def has_race(self, race_id: str) -> bool:
        """そのレースの払戻データがあるか。"""
        return race_id in self._races

    @property
    def race_count(self) -> int:
        return len(self._races)
