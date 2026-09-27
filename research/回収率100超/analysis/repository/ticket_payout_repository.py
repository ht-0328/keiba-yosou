"""1つの券種の確定払戻を、当たった買い目ごとに読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from ..tickets.ticket_kind import TicketKind
from .race_key_sql import JRA_ONLY, RID

_SQL = f"""
select try_cast({RID} as bigint) as rid, {{horses}},
    max(try_cast(払戻金 as integer)) as payout
from {{table}}
where 開催年 >= '{{first_year}}' and {JRA_ONLY} and try_cast(払戻金 as integer) > 0
    and try_cast(substr({{combo}}, 1, 2) as integer) > 0
group by all
"""


class TicketPayoutRepository:
    """券種の払戻の表から、当たった買い目と 100円あたりの払戻を読む。

    同着のときは当たりの買い目が2つ以上ある。どれも払戻の行があるので、そのまま全部読む。
    """

    def __init__(self, connection: duckdb.DuckDBPyConnection, first_year: int = 2016) -> None:
        self._connection = connection
        self._first_year = first_year

    def read(self, kind: TicketKind) -> pd.DataFrame:
        """``rid``・``h1``〜（券種の馬の数）・``payout`` の列。"""
        sql = _SQL.format(table=kind.payout_table, first_year=self._first_year,
                          horses=kind.horse_columns_sql(kind.payout_combo), combo=kind.payout_combo)
        return self._connection.execute(sql).fetch_df()
