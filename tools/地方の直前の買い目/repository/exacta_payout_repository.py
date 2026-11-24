"""馬単の的中の組と払戻を、開催日の範囲で読む（1 SQL）。同着なら1レースに複数の行。"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import pandas as pd

from 共通 import keys

_TABLE = "hr__馬単払戻"


@dataclass(frozen=True)
class ExactaPayoutRepository:
    """``race_id``（16桁の文字列）・``first``・``second``（馬番）・``payout``（100円あたりの払戻、円）。
    ``day_from``〜``day_to`` は YYYYMMDD（両端を含む）。"""

    con: duckdb.DuckDBPyConnection

    def load(self, day_from: str, day_to: str) -> pd.DataFrame:
        sql = f"""
            SELECT {keys.rid_expr()} AS race_id,
                   CAST(substr(組番, 1, 2) AS INTEGER) AS first, CAST(substr(組番, 3, 2) AS INTEGER) AS second,
                   CAST(払戻金 AS INTEGER) AS payout
            FROM {keys.q(_TABLE)}
            WHERE 開催年 || 開催月日 BETWEEN ? AND ? AND TRY_CAST(払戻金 AS INTEGER) > 0
        """
        return self.con.execute(sql, [day_from, day_to]).df()
