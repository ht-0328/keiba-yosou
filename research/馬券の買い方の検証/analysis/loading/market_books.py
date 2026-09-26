"""オッズと払戻の帳簿と、読めた数の数え上げ。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.shared.betting import TicketType

from ..settlement import OddsBook, PayoutBook


@dataclass(frozen=True)
class MarketBooks:
    """``OddsBook``・``PayoutBook`` と、期間で読めた数（券種ごとのオッズのあるレース数、払戻のあるレース数、不成立・返還の数）。"""

    odds_book: OddsBook
    payout_book: PayoutBook
    odds_races: dict[TicketType, int]
    payout_races: int
    void_counts: dict[TicketType, int]
    refunded_races: int
