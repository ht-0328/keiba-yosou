"""レースごとの、券種プールの大きさ（票数合計）を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from .race_key_sql import JRA_ONLY, RID

_SQL = f"""
with 単複枠 as (
    select {RID} as rid,
        max(try_cast(単勝票数合計 as double)) as 単勝プールの大きさ,
        max(try_cast(複勝票数合計 as double)) as 複勝プールの大きさ
    from o1 where 開催年 >= '{{first_year}}' and {JRA_ONLY} group by 1
),
馬連 as (
    select {RID} as rid, max(try_cast(馬連票数合計 as double)) as 馬連プールの大きさ
    from o2 where 開催年 >= '{{first_year}}' group by 1
),
ワイド as (
    select {RID} as rid, max(try_cast(ワイド票数合計 as double)) as ワイドプールの大きさ
    from o3 where 開催年 >= '{{first_year}}' group by 1
),
三連複 as (
    select {RID} as rid, max(try_cast("3連複票数合計" as double)) as "3連複プールの大きさ"
    from o5 where 開催年 >= '{{first_year}}' group by 1
),
三連単 as (
    select {RID} as rid, max(try_cast("3連単票数合計" as double)) as "3連単プールの大きさ"
    from o6 where 開催年 >= '{{first_year}}' group by 1
)
select 単複枠.*, 馬連.馬連プールの大きさ, ワイド.ワイドプールの大きさ,
    三連複."3連複プールの大きさ", 三連単."3連単プールの大きさ"
from 単複枠
left join 馬連 on 馬連.rid = 単複枠.rid
left join ワイド on ワイド.rid = 単複枠.rid
left join 三連複 on 三連複.rid = 単複枠.rid
left join 三連単 on 三連単.rid = 単複枠.rid
"""


class PoolSizeRepository:
    """レースごとの、券種ごとのプールの大きさを読む。

    プールが大きいほど多くの判断が値段に入っているので、値付けが正確になるはずである。
    実測では、3連単プールの中央値は複勝プールの 2倍以上あった。
    「どの券種から確率を取り出し、どの券種を買うか」を決める根拠になる。
    """

    def __init__(self, connection: duckdb.DuckDBPyConnection, first_year: int = 2016) -> None:
        self._connection = connection
        self._first_year = first_year

    def read(self) -> pd.DataFrame:
        """1行 = 1レース。"""
        return self._connection.execute(_SQL.format(first_year=self._first_year)).fetch_df()
