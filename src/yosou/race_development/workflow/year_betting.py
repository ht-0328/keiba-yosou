"""1年ぶんのレースの買い目を作り、払戻で精算する。"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from yosou.shared.betting import TicketType

from ..betting import TicketSettler
from ..betting import column_names as bet
from .group_fitter import ORDER_LAMBDA
from .race_betting import RaceBetting

#: 1年ぶんの予測の表の列（1行 = 1頭）。``bet`` の列に、レースID とならしの指数 λ を足したもの。
YEAR_COLUMNS: tuple[str, ...] = (
    bet.RACE_ID, bet.HORSE_NO, bet.WIN_PROBABILITY, bet.WIN_ODDS, bet.LEADER_PROBABILITY, ORDER_LAMBDA,
)


class YearBetting:
    """1年ぶんのレースについて、レースごとに印と買い目を作り（``RaceBetting``）、払戻と照らし合わせて精算する（設計書 05 の図6）。"""

    def __init__(self) -> None:
        self._race_betting = RaceBetting()
        self._settler = TicketSettler()

    def settle(self, year: int, horses: pd.DataFrame, odds: Mapping[TicketType, pd.DataFrame],
               payouts: Mapping[TicketType, pd.DataFrame], flags: pd.DataFrame) -> pd.DataFrame:
        """``horses`` はその年の予測（列 ``YEAR_COLUMNS``）。``odds``・``payouts`` は券種 → 確定オッズ・払戻の明細（その年ぶん）、
        ``flags`` は払戻のフラグ。戻り値は精算した買い目の表に、列 ``year`` を足したもの。
        """
        odds_rows = {ticket_type: table.groupby(bet.RACE_ID).indices for ticket_type, table in odds.items()}
        tickets = [
            self._race_tickets(race_id, race, odds, odds_rows)
            for race_id, race in horses.groupby(bet.RACE_ID, sort=False)
        ]
        settled = self._settler.settle(pd.concat(tickets, ignore_index=True), payouts, flags)
        return settled.assign(**{bet.YEAR: str(year)})

    def _race_tickets(self, race_id: str, race: pd.DataFrame, odds: Mapping[TicketType, pd.DataFrame],
                      odds_rows: Mapping[TicketType, Mapping[str, np.ndarray]]) -> pd.DataFrame:
        """1レースの買い目。"""
        race_odds = {
            ticket_type: odds[ticket_type].iloc[rows[race_id]] for ticket_type, rows in odds_rows.items() if race_id in rows
        }
        ordered = race.sort_values(bet.HORSE_NO).reset_index(drop=True)
        return self._race_betting.tickets(race_id, ordered, float(ordered[ORDER_LAMBDA].iloc[0]), race_odds)
