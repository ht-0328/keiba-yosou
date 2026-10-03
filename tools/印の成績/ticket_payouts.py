"""買い目に、確定の払戻とオッズを付ける。"""

from __future__ import annotations

from collections.abc import Iterable

import duckdb
import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.repository import PayoutRepository, RaceDayRange
from yosou.shared.repository.payout_repository import COMBO, YEN
from yosou.shared.repository.ticket_odds_repository import TicketOddsRepository

#: 付ける列（100円あたりの払戻。外れは 0。確定オッズ。買えない組（無投票・取消）は欠損値）。
PAYOUT, ODDS = "payout", "odds"


class TicketPayouts:
    """買い目の表（``MarkTickets.build``）に、確定の払戻（100円あたり）と確定オッズを付ける。

    払戻は券種ごとに期間の全レースぶん読んで（``PayoutRepository``）、買い目と組番で突き合わせる。同着で払戻が複数ある組はそれぞれの行に当たる。
    オッズは買い目の組だけを読む（``TicketOddsRepository``。トリガミの確かめに使う）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def attach(self, tickets: pd.DataFrame) -> pd.DataFrame:
        if tickets.empty:
            return tickets.assign(**{PAYOUT: pd.Series(dtype=float), ODDS: pd.Series(dtype=float)})
        days = RaceDayRange(tickets["race_date"].min().date(), tickets["race_date"].max().date())
        race_ids = set(tickets["race_id"].astype(str))
        parts = []
        for label, group in tickets.groupby("ticket_type", sort=False):
            ticket_type = TicketType.parse(label)
            payouts = self._payouts(ticket_type, days, race_ids)
            odds = TicketOddsRepository(self._con, ticket_type).read(group).rename(columns={"odds": ODDS})
            merged = group.merge(payouts, on=["race_id", "combo"], how="left").merge(odds, on=["race_id", "combo"], how="left")
            parts.append(merged)
        table = pd.concat(parts, ignore_index=True)
        table[PAYOUT] = table[PAYOUT].fillna(0.0).astype(float)
        return table

    def _payouts(self, ticket_type: TicketType, days: RaceDayRange, race_ids: Iterable[str]) -> pd.DataFrame:
        rows = PayoutRepository(self._con, ticket_type).read(days)
        rows = rows[rows["race_id"].astype(str).isin(set(race_ids))]
        return rows.groupby(["race_id", COMBO], as_index=False)[YEN].sum().rename(columns={COMBO: "combo", YEN: PAYOUT})
