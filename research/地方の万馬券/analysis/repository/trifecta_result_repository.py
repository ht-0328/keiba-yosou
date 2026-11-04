"""3連単の的中の組と払戻を、レースごとに読む（1 SQL）。同着があれば1レースに複数の行。"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import pandas as pd

from 共通 import keys

_TABLE = "hr__3連単払戻"


@dataclass(frozen=True)
class TrifectaResultRepository:
    """``race_id``（16桁の整数）・``first``・``second``・``third``（馬番）・``payout``（100円あたりの払戻、円）。"""

    con: duckdb.DuckDBPyConnection

    def load(self) -> pd.DataFrame:
        sql = f"""
            SELECT CAST({keys.rid_expr()} AS BIGINT) AS race_id,
                   CAST(substr(組番, 1, 2) AS INTEGER) AS first, CAST(substr(組番, 3, 2) AS INTEGER) AS second,
                   CAST(substr(組番, 5, 2) AS INTEGER) AS third, CAST(払戻金 AS INTEGER) AS payout
            FROM {keys.q(_TABLE)}
            WHERE CAST(払戻金 AS INTEGER) > 0
        """
        return self.con.execute(sql).df()
