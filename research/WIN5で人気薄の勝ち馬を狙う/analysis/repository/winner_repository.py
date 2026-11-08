"""レースの勝ち馬の馬番を読む（1 SQL）。"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from 共通 import keys


@dataclass(frozen=True)
class WinnerRepository:
    """確定着順が1着の馬の馬番（同着なら馬番の小さいほう）。まだ結果が無ければ 0。"""

    con: duckdb.DuckDBPyConnection

    def of(self, race_id: str) -> int:
        sql = f"""
        SELECT min(TRY_CAST({keys.q('馬番')} AS INTEGER)) FROM se
        WHERE {keys.rid_expr()} = ? AND {keys.q('確定着順')} = '01'
        """
        found = self.con.execute(sql, [race_id]).fetchone()
        return int(found[0]) if found and found[0] is not None else 0
