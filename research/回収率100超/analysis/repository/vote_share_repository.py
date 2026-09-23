"""票数から、単勝・複勝プールの配分を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from .race_key_sql import JRA_ONLY, RID

_SQL = f"""
with 票 as (
    select {RID} as rid, try_cast(馬番 as integer) as horse_no,
        try_cast(票数 as double) as votes
    from {{table}}
    where 開催年 >= '{{first_year}}' and {JRA_ONLY} and try_cast(票数 as double) > 0
),
レース合計 as (select rid, sum(votes) as total from 票 group by rid)
select 票.rid, 票.horse_no, 票.votes / レース合計.total as "{{column}}"
from 票 join レース合計 on レース合計.rid = 票.rid
"""

#: 作る列 → （元DB の票数の子表, 中間データのファイル名に使う短い名前）。
VOTE_SHARES: dict[str, tuple[str, str]] = {
    "単勝票数の配分": ("h1__単勝票数", "win_votes"),
    "複勝票数の配分": ("h1__複勝票数", "place_votes"),
}


class VoteShareRepository:
    """票数から、レース内の配分（合計1）を読む。

    発表オッズは 0.1 刻みに丸められていて、複勝は「最低〜最高」の幅でしか出ない。
    人気馬の帯では、この丸めが確率の細かい違いを消してしまう。
    票数はその馬に入った金そのものなので、丸めのない配分が得られる。
    """

    def __init__(self, connection: duckdb.DuckDBPyConnection, first_year: int = 2016) -> None:
        self._connection = connection
        self._first_year = first_year

    def read(self, column: str) -> pd.DataFrame:
        """``rid``・``horse_no``・``column`` の3列。"""
        table, _ = VOTE_SHARES[column]
        sql = _SQL.format(table=table, first_year=self._first_year, column=column)
        return self._connection.execute(sql).fetch_df()
