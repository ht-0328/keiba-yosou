"""3連単の払戻を、レースごとに読む（1 SQL）。"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import pandas as pd

from 共通 import keys

#: 3連単払戻の表。同着があると連番 2 以降にも行があるが、配当の帯は 1 つめの組で決める。
_TABLE = "hr__3連単払戻"
_FIRST = 1


@dataclass(frozen=True)
class TrifectaPayoutRepository:
    """``race_id`` と ``trifecta_payout``（100円あたりの払戻、円。発売が無いレースは出ない）。"""

    con: duckdb.DuckDBPyConnection

    def load(self) -> pd.DataFrame:
        sql = f"""
            SELECT {keys.rid_expr()} AS race_id, max(CAST(払戻金 AS INTEGER)) AS trifecta_payout
            FROM {keys.q(_TABLE)}
            WHERE _連番 = {_FIRST} AND CAST(払戻金 AS INTEGER) > 0
            GROUP BY 1
        """
        return self.con.execute(sql).df()
