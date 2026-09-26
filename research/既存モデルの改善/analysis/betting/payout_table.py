"""期間の全レースの、7つの券種の払戻を読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.repository import PayoutRepository, RaceDayRange
from yosou.shared.repository.payout_repository import COMBO, YEN

from .candidate_columns import RACE, TICKET
from .candidate_columns import COMBO as COMBO_COLUMN

#: 払戻の列の名前（100円あたりの円。外れは 0）。
PAYOUT = "払戻"


class PayoutTable:
    """研究「馬券の買い方の検証」の ``PayoutRepository``（1 SQL = 1クラス）で、7つの券種の払戻を読み、
    （レースID, 券種, 組番）→ 払戻 の表にする。同じ組番が複数あれば（同着）足す。"""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, first_day: date, last_day: date) -> pd.DataFrame:
        days = RaceDayRange(first_day, last_day)
        frames = [self._one(ticket, days) for ticket in TicketType]
        return pd.concat(frames, ignore_index=True)

    def _one(self, ticket: TicketType, days: RaceDayRange) -> pd.DataFrame:
        raw = PayoutRepository(self._con, ticket).read(days)
        grouped = raw.groupby(["race_id", COMBO], as_index=False)[YEN].sum()
        return pd.DataFrame({RACE: grouped["race_id"].astype(str), TICKET: ticket.label,
                             COMBO_COLUMN: grouped[COMBO].astype(str), PAYOUT: grouped[YEN].astype(float)})
