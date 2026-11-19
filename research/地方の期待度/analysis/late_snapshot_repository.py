"""締め切り後に取り込んだオッズの断面（発表月日時分の入った最終・確定）のあるレースを読む（1 SQL）。"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from 共通 import keys

#: 最終・確定のデータ区分。月曜の確定（5）は発表月日時分が 0 なので、条件の「発表月日時分 > 0」で外れる。
_AFTER_CLOSE = ("3", "4")
_HEADER = "o6"


@dataclass(frozen=True)
class LateSnapshotRepository:
    """``load(day_from)`` は、``day_from``（YYYYMMDD）以降のレースのうち、3連単のオッズに締め切り後の断面があるレースの rid の集まり。
    そのレースは「最新の発表」が通知のときの断面でないので、通知のときの推奨買目を作り直せない。"""

    con: duckdb.DuckDBPyConnection

    def load(self, day_from: str) -> frozenset[str]:
        sql = f"""
            SELECT DISTINCT {keys.rid_expr()} AS race_id
            FROM {_HEADER}
            WHERE 開催年 || 開催月日 >= ? AND データ区分 IN {keys.sql_list(_AFTER_CLOSE)} AND TRY_CAST(発表月日時分 AS BIGINT) > 0
        """
        return frozenset(str(rid) for (rid,) in self.con.execute(sql, [day_from]).fetchall())
