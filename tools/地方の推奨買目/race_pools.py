"""1レースの票の表: 発走前の最新の発表のオッズ（3連単・馬単・3連複・複勝）と全頭の予想の馬の表から ``PoolTables`` を組む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from .pool_tables import PoolTables
from .pool_tables_builder import PoolTablesBuilder
from .repository import AnnouncedTicketOddsRepository, AnnouncedTrifectaOddsRepository


class RacePools:
    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def build(self, rid: str, horses: pd.DataFrame) -> PoolTables:
        """3連単のオッズがまだ無ければ ``LookupError``（速報 0B30 を取り込む前）。"""
        trifecta = AnnouncedTrifectaOddsRepository(self._con).load(rid)
        if trifecta.empty:
            raise LookupError(f"3連単のオッズがまだ DB にありません（{rid}）。速報 0B30 を取り込んでください")
        exacta, trio, place = (AnnouncedTicketOddsRepository(self._con, ticket).load(rid) for ticket in ("馬単", "3連複", "複勝"))
        return PoolTablesBuilder().build(horses, trifecta, exacta, trio, place)
