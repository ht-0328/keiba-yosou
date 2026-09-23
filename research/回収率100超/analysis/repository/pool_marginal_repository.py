"""組み合わせ券種のオッズから、馬ごとの確率を取り出す。"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import pandas as pd

from .race_key_sql import JRA_ONLY, RID

#: 1頭目だけを見る券種（馬単・3連単）の SQL。組番の先頭2桁が1着の馬番。
_FIRST_HORSE_SQL = f"""
with オッズ as (
    select {RID} as rid, substr(組番, 1, 2) as horse_text, 1.0 / ({{price}}) as inverse
    from {{table}}
    where 開催年 >= '{{first_year}}' and {JRA_ONLY} and ({{price}}) > 0
),
レース合計 as (select rid, sum(inverse) as total from オッズ group by rid)
select オッズ.rid, try_cast(オッズ.horse_text as integer) as horse_no,
    sum(オッズ.inverse) / max(レース合計.total) as "{{column}}"
from オッズ join レース合計 on レース合計.rid = オッズ.rid
group by オッズ.rid, オッズ.horse_text
"""

#: 組に入っている馬すべてを見る券種（馬連・ワイド・3連複・複勝）の SQL。順不同なので、組の各馬に同じ値を配る。
_ALL_HORSES_SQL = f"""
with オッズ as (
    select {RID} as rid, {{combo}} as combo, 1.0 / ({{price}}) as inverse
    from {{table}}
    where 開催年 >= '{{first_year}}' and {JRA_ONLY} and ({{price}}) > 0
),
レース合計 as (select rid, sum(inverse) as total from オッズ group by rid),
ばらす as (
    select オッズ.rid,
        try_cast(substr(オッズ.combo, (位置.i - 1) * 2 + 1, 2) as integer) as horse_no,
        オッズ.inverse
    from オッズ cross join (select unnest(range(1, {{horses_per_combo}} + 1)) as i) 位置
)
select ばらす.rid, ばらす.horse_no, sum(ばらす.inverse) / max(レース合計.total) as "{{column}}"
from ばらす join レース合計 on レース合計.rid = ばらす.rid
group by ばらす.rid, ばらす.horse_no
"""

#: 単一のオッズ列を持つ券種の、値段の式（元DB のオッズは 10倍の整数）。
_SINGLE_ODDS = "try_cast(オッズ as double) / 10.0"
#: 幅（最低〜最高）でしか出ない券種（複勝・ワイド）の、値段の式。中間を使う。
_RANGE_ODDS = "(try_cast(最低オッズ as double) + try_cast(最高オッズ as double)) / 20.0"


@dataclass(frozen=True)
class PoolMarginal:
    """どの券種から、どの意味の確率を、どうやって取り出すか。

    - ``key``: 中間データのファイル名に使う短い名前。
    - ``column``: 作る列の名前。
    - ``table``: 元DB のオッズの子表。
    - ``combo``: 組を表す列の名前（``組番``。複勝だけ ``馬番``）。
    - ``price``: 払戻倍率にする式。1つのオッズ列を持つ券種と、幅で出る券種（複勝・ワイド）で違う。
    - ``horses_per_combo``: 組番に入っている馬の数（複勝は1、馬連・ワイドは2、3連複・3連単は3）。
    - ``first_horse_only``: 1着の馬だけを見るか（馬単・3連単は True）。
    """

    key: str
    column: str
    table: str
    combo: str
    price: str
    horses_per_combo: int
    first_horse_only: bool


#: 取り出す確率の一覧。3連単・3連複は JRA でいちばん売れる券種なので、いちばん情報が多いと考える。
POOL_MARGINALS: tuple[PoolMarginal, ...] = (
    PoolMarginal("trifecta_win", "3連単から見た勝率", "o6__3連単オッズ", "組番", _SINGLE_ODDS, 3, True),
    PoolMarginal("exacta_win", "馬単から見た勝率", "o4__馬単オッズ", "組番", _SINGLE_ODDS, 2, True),
    PoolMarginal("trio_top3", "3連複から見た3着以内率", "o5__3連複オッズ", "組番", _SINGLE_ODDS, 3, False),
    PoolMarginal("quinella_top2", "馬連から見た2着以内率", "o2__馬連オッズ", "組番", _SINGLE_ODDS, 2, False),
    PoolMarginal("wide_top3", "ワイドから見た3着以内率", "o3__ワイドオッズ", "組番", _RANGE_ODDS, 2, False),
    PoolMarginal("place_top3", "複勝から見た3着以内率", "o1__複勝オッズ", "馬番", _RANGE_ODDS, 1, False),
)


class PoolMarginalRepository:
    """1つの券種のオッズから、馬ごとの確率を1列ぶん読む。

    オッズの逆数は「その買い目に、どれだけの金が入ったか」の代わりになる。レース内で合計1にそろえると、
    市場がその買い目に付けた確率になる。それを馬ごとに足し合わせると、「その馬が1着になる確率」
    （馬単・3連単）や「その馬が組に入る確率」（馬連・3連複・ワイド）が出る。
    """

    def __init__(self, connection: duckdb.DuckDBPyConnection, first_year: int = 2016) -> None:
        self._connection = connection
        self._first_year = first_year

    def read(self, marginal: PoolMarginal) -> pd.DataFrame:
        """``rid``・``horse_no``・``marginal.column`` の3列。"""
        template = _FIRST_HORSE_SQL if marginal.first_horse_only else _ALL_HORSES_SQL
        sql = template.format(table=marginal.table, first_year=self._first_year,
                              column=marginal.column, combo=marginal.combo, price=marginal.price,
                              horses_per_combo=marginal.horses_per_combo)
        return self._connection.execute(sql).fetch_df()
