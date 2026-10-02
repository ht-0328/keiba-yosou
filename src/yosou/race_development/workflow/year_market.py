"""1年ぶんの、7券種の確定オッズと払戻を読む。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import duckdb
import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.repository import FinalOddsRepository, PayoutFlagRepository, PayoutRepository, RaceDayRange


@dataclass(frozen=True)
class YearMarket:
    """1年ぶんの、券種ごとの確定オッズと払戻の明細と、払戻のフラグ。"""

    odds: dict[TicketType, pd.DataFrame]
    payouts: dict[TicketType, pd.DataFrame]
    flags: pd.DataFrame

    @classmethod
    def read(cls, con: duckdb.DuckDBPyConnection, year: int) -> YearMarket:
        """その年の1月1日から12月31日まで。3連単のオッズは1年で千万行を超えるので、1年ずつ読む。"""
        days = RaceDayRange(date(year, 1, 1), date(year, 12, 31))
        return cls(
            odds={ticket_type: FinalOddsRepository(con, ticket_type).read(days) for ticket_type in TicketType},
            payouts={ticket_type: PayoutRepository(con, ticket_type).read(days) for ticket_type in TicketType},
            flags=PayoutFlagRepository(con).read(days),
        )
