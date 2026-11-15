"""1レースの券種ごとの組の確率に、その券種の最新の発表のオッズを付ける。"""

from __future__ import annotations

import duckdb
import pandas as pd

from .repository import AnnouncedTicketOddsRepository
from .ticket_probabilities import TICKET_KEYS

_TRIFECTA = "3連単"


class TicketPricer:
    """``priced(ticket, probabilities, combos, rid)`` は、組の確率の表（``TicketProbabilities`` の1券種）に最新のオッズを付けた表。
    3連単は ``combos``（``PositionModel.predict`` の表。3連単のオッズつき）の列名を ``a``・``b``・``c`` にしたもの。オッズの無い組は買えないので落とす。"""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def priced(self, ticket: str, probabilities: pd.DataFrame, combos: pd.DataFrame, rid: str) -> pd.DataFrame:
        if ticket == _TRIFECTA:
            return combos.rename(columns={"first": "a", "second": "b", "third": "c"})
        odds = AnnouncedTicketOddsRepository(self._con, ticket).load(rid)
        return probabilities.merge(odds, on=["race_id", *TICKET_KEYS[ticket]], how="inner")
