"""レースごとの出走馬の数・馬番の決まった数・馬体重の出ている数（``se``）を読む。"""

from __future__ import annotations

import duckdb

from 共通 import keys, raw
from 共通.race_signals.race_scope import RaceScope


class EntryCountRepository:
    """``se`` から、範囲のレースごとに 出走馬の数（取消を含む）・馬番の決まった数・馬体重の出ている数 を読む。

    同じ馬に複数のデータ区分の行があれば、いちばん新しい行だけを数える（出馬表の部品 ``card`` と同じ）。
    馬体重は ``000``（未発表）と ``999``（計量不能）を「出ていない」と見る（``raw.body_weight`` と同じ）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, scope: RaceScope) -> dict[str, tuple[int, int, int]]:
        """rid → （出走馬の数, 馬番の決まった数, 馬体重の出ている数）。出走馬の行が無いレースは入らない。"""
        where, params = scope.where()
        horse_no = f"TRY_CAST({keys.q('馬番')} AS INTEGER)"
        body_weight = keys.q("馬体重")
        weighed = f"TRY_CAST(body_weight AS INTEGER) > 0 AND body_weight NOT IN {keys.sql_list(raw.NO_BODY_WEIGHT)}"
        sql = f"""
        WITH latest AS (
            SELECT {keys.rid_expr()} AS rid, {horse_no} AS horse_no, {body_weight} AS body_weight
            FROM se
            WHERE {where}
            {keys.latest_qualify((*keys.RACE_KEY, keys.HORSE_KEY))}
        )
        SELECT rid, count(*), count(*) FILTER (horse_no > 0), count(*) FILTER ({weighed})
        FROM latest
        GROUP BY rid
        """
        return {rid: (entries, numbered, weighed) for rid, entries, numbered, weighed in self._con.execute(sql, params).fetchall()}
