"""調教師の所属（招待地域名）を、調教師マスタ地方から読む（1 SQL）。"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import pandas as pd

_TABLE = "ch"


@dataclass(frozen=True)
class TrainerAreaRepository:
    """``trainer_code`` と ``trainer_area``（船橋・大井・小林・西脇 など。空の調教師は出ない）。"""

    con: duckdb.DuckDBPyConnection

    def load(self) -> pd.DataFrame:
        sql = f"""
            SELECT 調教師コード AS trainer_code, max(招待地域名) AS trainer_area
            FROM {_TABLE}
            WHERE 招待地域名 <> ''
            GROUP BY 1
        """
        return self.con.execute(sql).df()
