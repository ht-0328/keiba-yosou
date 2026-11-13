"""抑えの 3連複の買い目に、確定の払戻（100円あたり）を付ける。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import duckdb
import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.repository import PayoutRepository, RaceDayRange
from yosou.shared.repository.payout_repository import COMBO, YEN


@dataclass(frozen=True)
class HedgeSettlement:
    """``payouts`` は 3連複の払戻の表（race_id・combo・yen）。``load`` で元DB から期間ぶん読む。"""

    payouts: pd.DataFrame

    def settle(self, tickets: pd.DataFrame) -> pd.DataFrame:
        table = self.payouts.groupby(["race_id", COMBO], as_index=False)[YEN].sum().rename(columns={COMBO: "combo", YEN: "payout"})
        merged = tickets.merge(table, on=["race_id", "combo"], how="left")
        merged["payout"] = merged["payout"].fillna(0.0).astype(float)
        return merged

    @staticmethod
    def load(con: duckdb.DuckDBPyConnection, first: date, last: date) -> pd.DataFrame:
        rows = PayoutRepository(con, TicketType.TRIO).read(RaceDayRange(first, last))
        return rows.astype({"race_id": str})
