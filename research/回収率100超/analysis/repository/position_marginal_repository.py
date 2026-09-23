"""3連単・馬単のプールから、「何着になるか」を着順ごとに読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from .race_key_sql import JRA_ONLY, RID

_SQL = f"""
with オッズ as (
    select {RID} as rid, 組番 as combo, 1.0 / (try_cast(オッズ as double) / 10.0) as inverse
    from {{table}}
    where 開催年 >= '{{first_year}}' and {JRA_ONLY} and try_cast(オッズ as double) > 0
),
レース合計 as (select rid, sum(inverse) as total from オッズ group by rid),
着順ごと as (
    select オッズ.rid,
        try_cast(substr(オッズ.combo, (位置.i - 1) * 2 + 1, 2) as integer) as horse_no,
        位置.i as position, オッズ.inverse
    from オッズ cross join (select unnest(range(1, {{positions}} + 1)) as i) 位置
)
select 着順ごと.rid, 着順ごと.horse_no,
{{columns}}
from 着順ごと join レース合計 on レース合計.rid = 着順ごと.rid
group by 着順ごと.rid, 着順ごと.horse_no
"""

#: 短い名前 → （元DB の表, 着順の数, 作る列の名前）。
POSITION_MARGINALS: dict[str, tuple[str, int, tuple[str, ...]]] = {
    "trifecta_positions": ("o6__3連単オッズ", 3, ("3連単の1着率", "3連単の2着率", "3連単の3着率")),
    "exacta_positions": ("o4__馬単オッズ", 2, ("馬単の1着率", "馬単の2着率")),
}


class PositionMarginalRepository:
    """着順つきの券種（3連単・馬単）から、「その馬が N 着になる確率」を着順ごとに読む。

    勝率だけに潰すと、「勝つほどではないが上位には来る」という市場の見方が消える。
    3連単の買い目には着順の情報が入っているので、1着ぶん・2着ぶん・3着ぶんを別々に足す。
    """

    def __init__(self, connection: duckdb.DuckDBPyConnection, first_year: int = 2016) -> None:
        self._connection = connection
        self._first_year = first_year

    def read(self, key: str) -> pd.DataFrame:
        """``rid``・``horse_no`` と、着順ごとの確率の列。"""
        table, positions, columns = POSITION_MARGINALS[key]
        pieces = ",\n".join(
            f'    sum(case when 着順ごと.position = {index + 1} then 着順ごと.inverse else 0 end)'
            f' / max(レース合計.total) as "{column}"'
            for index, column in enumerate(columns))
        sql = _SQL.format(table=table, first_year=self._first_year, positions=positions,
                          columns=pieces)
        return self._connection.execute(sql).fetch_df()
