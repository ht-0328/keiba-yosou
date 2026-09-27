"""1つの券種の確定オッズを、買い目1点ずつ、1年ぶん読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from ..tickets.ticket_kind import TicketKind
from .race_key_sql import JRA_ONLY, RID

_SQL = f"""
select try_cast({RID} as bigint) as rid, {{horses}}, ({{price}}) as odds
from {{table}}
where 開催年 = '{{year}}' and {JRA_ONLY} and ({{price}}) > 0
"""


class TicketOddsRepository:
    """券種のオッズの表から、買い目ごとの確定オッズを読む。

    3連単は1年で数百万点あるので、1年ずつ読む。レースの鍵（rid）は 16桁の整数にして、表を軽くする。
    ワイドは最低オッズを読む（受け取る額は、あとで帯ごとの倍率で見積もる）。
    """

    def __init__(self, connection: duckdb.DuckDBPyConnection) -> None:
        self._connection = connection

    def read(self, kind: TicketKind, year: int) -> pd.DataFrame:
        """``rid``・``h1``〜（券種の馬の数）・``odds`` の列。"""
        sql = _SQL.format(table=kind.odds_table, year=year,
                          horses=kind.horse_columns_sql(kind.odds_combo), price=kind.odds_price)
        return self._connection.execute(sql).fetch_df()
