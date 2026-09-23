"""JRA-VAN のマイニング予想（タイム型・対戦型）を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from .race_key_sql import RID

_SQL = f"""
with タイム型 as (
    select {RID} as rid, try_cast(馬番 as integer) as horse_no,
        avg(try_cast("予想走破タイム" as double)) as predicted_time,
        avg(try_cast("予想誤差(信頼度)＋" as double)) as error_plus,
        avg(try_cast("予想誤差(信頼度)－" as double)) as error_minus
    from dm__マイニング予想 where 開催年 >= '{{first_year}}' group by 1, 2
),
対戦型 as (
    select {RID} as rid, try_cast(馬番 as integer) as horse_no,
        avg(try_cast("予測スコア" as double)) as mining_score
    from tm__マイニング予想 where 開催年 >= '{{first_year}}' group by 1, 2
)
select coalesce(タイム型.rid, 対戦型.rid) as rid,
    coalesce(タイム型.horse_no, 対戦型.horse_no) as horse_no,
    タイム型.predicted_time, タイム型.error_plus, タイム型.error_minus, 対戦型.mining_score
from タイム型 full outer join 対戦型
    on タイム型.rid = 対戦型.rid and タイム型.horse_no = 対戦型.horse_no
"""


class MiningRepository:
    """マイニング予想を1行 = 1頭で読む。

    タイム型（``dm``）は予想走破タイムと、その誤差（信頼度）。対戦型（``tm``）は予測スコア（0〜999）。
    どちらも JRA-VAN が発表する予想で、馬券を買う人の一部しか見ていない。市場に織り込まれ切っていない
    情報が残っているかを測るために読む。
    """

    def __init__(self, connection: duckdb.DuckDBPyConnection, first_year: int = 2016) -> None:
        self._connection = connection
        self._first_year = first_year

    def read(self) -> pd.DataFrame:
        return self._connection.execute(_SQL.format(first_year=self._first_year)).fetch_df()
