"""券種ごとの確定の払戻を期間ぶん1回だけ読み、買い目に付ける。"""

from __future__ import annotations

import duckdb
import pandas as pd

from yosou.shared.betting import ticket_kind
from yosou.shared.repository import PayoutRepository, RaceDayRange
from yosou.shared.repository.payout_repository import COMBO, YEN

from 印の成績.ticket_payouts import PAYOUT


class PayoutTable:
    """道具「印の成績」の ``TicketPayouts`` と同じ払戻（100円あたり。同着は組ごとに合計、外れは 0）を、券種ごとに1回だけ読んで覚える。

    ``attach`` は買い目の表（列 ``race_id``・``ticket_type``・``combo`` …）に列 ``payout`` を付ける。オッズは付けない（``OddsCache``）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, days: RaceDayRange, race_ids: pd.Series) -> None:
        self._con = con
        self._days = days
        self._race_ids = set(race_ids.astype(str))
        self._tables: dict[str, pd.DataFrame] = {}

    def attach(self, tickets: pd.DataFrame) -> pd.DataFrame:
        if tickets.empty:
            return tickets.assign(**{PAYOUT: pd.Series(dtype=float)})
        parts = [group.merge(self._table(label), on=["race_id", "combo"], how="left") for label, group in tickets.groupby("ticket_type", sort=False)]
        table = pd.concat(parts, ignore_index=True)
        table[PAYOUT] = table[PAYOUT].fillna(0.0).astype(float)
        return table

    def _table(self, label: str) -> pd.DataFrame:
        if label not in self._tables:
            rows = PayoutRepository(self._con, ticket_kind(label)).read(self._days)
            rows = rows[rows["race_id"].astype(str).isin(self._race_ids)]
            grouped = rows.groupby(["race_id", COMBO], as_index=False)[YEN].sum().rename(columns={COMBO: "combo", YEN: PAYOUT})
            self._tables[label] = grouped.astype({"race_id": str, "combo": str})
        return self._tables[label]
