"""券種（単勝・複勝・枠連・馬連・ワイド・馬単・3連複）の、1レースの最新の発表のオッズを全部の組について読む（1 SQL のひな形を券種で埋める）。"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import pandas as pd

from 共通 import keys

from .ticket_odds_repository import _SPECS, combo_columns


@dataclass(frozen=True)
class AnnouncedTicketOddsRepository:
    """``race_id``（16桁の整数）・``a``（・``b``・``c``）・``odds``（倍。複勝・ワイドは ``odds_lo``・``odds_hi``）。
    発表月日時分がいちばん新しい断面（発走前なら直前の速報、終わったレースなら確定）。発売の無い組は出ない。"""

    con: duckdb.DuckDBPyConnection
    ticket: str

    def load(self, rid: str) -> pd.DataFrame:
        head, detail, kind, odds_columns = _SPECS[self.ticket]
        if len(odds_columns) == 1:
            odds_sql = f"TRY_CAST(d.{keys.q(odds_columns[0])} AS DOUBLE) / 10.0 AS odds"
        else:
            odds_sql = (f"TRY_CAST(d.{keys.q(odds_columns[0])} AS DOUBLE) / 10.0 AS odds_lo, "
                        f"TRY_CAST(d.{keys.q(odds_columns[1])} AS DOUBLE) / 10.0 AS odds_hi")
        sql = f"""
            WITH latest AS (
                SELECT 発表月日時分 FROM {head} h WHERE {keys.rid_expr('h')} = ? ORDER BY 発表月日時分 DESC LIMIT 1
            )
            SELECT CAST({keys.rid_expr('d')} AS BIGINT) AS race_id, {', '.join(combo_columns(kind, 'd'))}, {odds_sql}
            FROM {keys.q(detail)} d
            JOIN latest l ON d.発表月日時分 = l.発表月日時分
            WHERE {keys.rid_expr('d')} = ? AND TRY_CAST(d.{keys.q(odds_columns[0])} AS DOUBLE) > 0
        """
        return self.con.execute(sql, [rid, rid]).df()
