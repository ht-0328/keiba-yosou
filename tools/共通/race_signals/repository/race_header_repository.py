"""レースの見出し（``ra``）を、範囲のレースぶん読む。"""

from __future__ import annotations

from typing import Any

import duckdb

from 共通 import keys
from 共通.race_signals.race_scope import RaceScope

#: 返す列の名前（並びは SQL の SELECT と同じ）。
COLUMNS: tuple[str, ...] = (
    "rid", "race_date", "venue_code", "race_no", "post", "race_name", "cond_code", "grade", "track", "stage", "turf", "dirt",
)


class RaceHeaderRepository:
    """``ra`` から、範囲のレースの見出しを1レース1行で読む。同じレースに複数のデータ区分の行があれば、いちばん新しい行。"""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, scope: RaceScope) -> list[dict[str, Any]]:
        """開催日・競馬場・レース番号の順。列は ``COLUMNS``。"""
        where, params = scope.where()
        sql = f"""
        SELECT {keys.rid_expr()} AS rid, {keys.race_date_expr()} AS race_date, {keys.q('競馬場コード')} AS venue_code,
               CAST({keys.q('レース番号')} AS INTEGER) AS race_no, {keys.q('発走時刻')} AS post, trim({keys.q('競走名本題')}) AS race_name,
               {keys.q('競走条件コード 最若年条件')} AS cond_code, {keys.q('グレードコード')} AS grade, {keys.q('トラックコード')} AS track,
               {keys.q('データ区分')} AS stage, {keys.q('芝馬場状態コード')} AS turf, {keys.q('ダート馬場状態コード')} AS dirt
        FROM ra
        WHERE {where}
        {keys.latest_qualify(keys.RACE_KEY)}
        ORDER BY race_date, venue_code, race_no
        """
        return [dict(zip(COLUMNS, row)) for row in self._con.execute(sql, params).fetchall()]
