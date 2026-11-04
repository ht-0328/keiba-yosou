"""馬の所属（招待地域名）を、競走馬マスタ地方から読む（1 SQL）。調教師マスタに無い調教師の馬の、所属の代わりに使う。"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import pandas as pd

from 共通 import keys

_TABLE = "nu"


@dataclass(frozen=True)
class HorseAreaRepository:
    """``horse_id`` と ``horse_area``（マスタの時点の所属。空の馬は出ない）。"""

    con: duckdb.DuckDBPyConnection

    def load(self) -> pd.DataFrame:
        sql = f"""
            SELECT {keys.q(keys.HORSE_KEY)} AS horse_id, max(招待地域名) AS horse_area
            FROM {_TABLE}
            WHERE 招待地域名 <> ''
            GROUP BY 1
        """
        return self.con.execute(sql).df()
