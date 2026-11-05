"""3連単の、1レースの最新の発表のオッズを全部の組について読む（1 SQL）。"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import pandas as pd

from 共通 import keys

_HEAD, _DETAIL = "o6", "o6__3連単オッズ"


@dataclass(frozen=True)
class AnnouncedTrifectaOddsRepository:
    """``race_id``（16桁の整数）・``first``・``second``・``third``（馬番）・``odds``（倍）。
    発表月日時分がいちばん新しい断面（発走前なら直前の速報、終わったレースなら確定）。発売の無い組は出ない。"""

    con: duckdb.DuckDBPyConnection

    def load(self, rid: str) -> pd.DataFrame:
        sql = f"""
            WITH latest AS (
                SELECT 発表月日時分 FROM {_HEAD} h WHERE {keys.rid_expr('h')} = ? ORDER BY 発表月日時分 DESC LIMIT 1
            )
            SELECT CAST({keys.rid_expr('d')} AS BIGINT) AS race_id,
                   CAST(substr(d.組番, 1, 2) AS INTEGER) AS first, CAST(substr(d.組番, 3, 2) AS INTEGER) AS second,
                   CAST(substr(d.組番, 5, 2) AS INTEGER) AS third,
                   TRY_CAST(d.オッズ AS DOUBLE) / 10.0 AS odds
            FROM {keys.q(_DETAIL)} d
            JOIN latest l ON d.発表月日時分 = l.発表月日時分
            WHERE {keys.rid_expr('d')} = ? AND TRY_CAST(d.オッズ AS DOUBLE) > 0
        """
        return self.con.execute(sql, [rid, rid]).df()
