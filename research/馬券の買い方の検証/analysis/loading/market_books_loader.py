"""元DB から確定オッズ・払戻・フラグを読んで帳簿にする。"""

from __future__ import annotations

from collections.abc import Callable

import duckdb

from yosou.shared.betting import TicketType
from yosou.shared.repository import REFUNDED, FinalOddsRepository, PayoutFlagRepository, PayoutRepository, RaceDayRange, void_column

from ..settlement import OddsBook, PayoutBook
from .market_books import MarketBooks


class MarketBooksLoader:
    """期間の7券種の確定オッズと払戻の明細、払戻のフラグを元DB から読み、``OddsBook``・``PayoutBook`` にする。

    3連単のオッズ（9,000万行）は期間の親との結合で読むので、数十秒かかる。``progress`` に進み具合を出す関数を渡せる。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, progress: Callable[[str], None] | None = None) -> None:
        self._con = con
        self._progress = progress or (lambda message: None)

    def load(self, days: RaceDayRange) -> MarketBooks:
        odds = {ticket_type: self._read_odds(ticket_type, days) for ticket_type in TicketType}
        payouts = {ticket_type: PayoutRepository(self._con, ticket_type).read(days) for ticket_type in TicketType}
        self._progress("払戻のフラグ")
        flags = PayoutFlagRepository(self._con).read(days)
        return MarketBooks(
            OddsBook(odds), PayoutBook(payouts, flags),
            odds_races={ticket_type: int(table["race_id"].nunique()) for ticket_type, table in odds.items()},
            payout_races=int(flags["race_id"].nunique()),
            void_counts={ticket_type: int(flags[void_column(ticket_type)].sum()) for ticket_type in TicketType},
            refunded_races=int(flags[REFUNDED].sum()),
        )

    def _read_odds(self, ticket_type: TicketType, days: RaceDayRange):
        self._progress(f"{ticket_type.label}の確定オッズ")
        return FinalOddsRepository(self._con, ticket_type).read(days)
