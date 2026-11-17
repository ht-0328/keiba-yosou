"""単勝の払戻を、開催日の範囲で読む（1 SQL）。同着なら1レースに複数の行。"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import pandas as pd

from 共通 import keys

_TABLE = "hr__単勝払戻"


@dataclass(frozen=True)
class WinPayoutRepository:
    """``race_id``（16桁の文字列）・``horse_no``・``payout``（100円あたりの払戻、円）。``day_from``〜``day_to`` は YYYYMMDD（両端を含む）。"""

    con: duckdb.DuckDBPyConnection

    def load(self, day_from: str, day_to: str) -> pd.DataFrame:
        sql = f"""
            SELECT {keys.rid_expr()} AS race_id, CAST(馬番 AS INTEGER) AS horse_no, CAST(払戻金 AS INTEGER) AS payout
            FROM {keys.q(_TABLE)}
            WHERE 開催年 || 開催月日 BETWEEN ? AND ? AND TRY_CAST(馬番 AS INTEGER) > 0 AND TRY_CAST(払戻金 AS INTEGER) > 0
        """
        return self.con.execute(sql, [day_from, day_to]).df()
