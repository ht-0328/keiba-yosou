"""速報の出走取消・競走除外を読む。"""

from __future__ import annotations

import duckdb

from 共通 import facts, keys

_NEEDED_COLUMNS = (*keys.RACE_KEY, "データ区分", "馬番")
#: 速報（av）のデータ区分。1 出走取消・2 競走除外。
_SCRATCH_STAGES: tuple[str, ...] = ("1", "2")


class ScratchRepository:
    """速報の出走取消・競走除外（av）から、1レースで出走しなくなった馬の馬番を読む。"""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, race_id: str) -> list[int]:
        """出走しなくなった馬の馬番（小さい順）。速報が無ければ空のリスト。"""
        table = facts.optional_relation(self._con, "av", _NEEDED_COLUMNS)
        sql = f"""
        SELECT DISTINCT TRY_CAST({keys.q('馬番')} AS INTEGER) AS horse_no
        FROM {table}
        WHERE {keys.rid_expr()} = ?
          AND {keys.q('データ区分')} IN {keys.sql_list(_SCRATCH_STAGES)}
        ORDER BY horse_no
        """
        rows = self._con.execute(sql, [race_id]).fetchall()
        return [horse_no for (horse_no,) in rows if horse_no is not None]
