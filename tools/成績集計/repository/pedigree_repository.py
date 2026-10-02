"""馬ごとの父・父の父・母父の名前を、競走馬マスタの3代血統情報から直接読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts

#: 3代血統情報の連番（JV-Data 仕様書「競走馬マスタ」の3代血統情報の並び）。1 父・3 父の父・5 母父。
_COLUMNS = ("血統登録番号", "_連番", "馬名")


class PedigreeRepository:
    """1行 = 1頭（``horse_id``・``sire``・``grandsire``・``damsire``）。表が無い DB では空の表。"""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self) -> pd.DataFrame:
        table = facts.optional_relation(self._con, "um__3代血統情報", _COLUMNS)
        return self._con.execute(f"""
            SELECT "血統登録番号" AS horse_id,
                   max(CASE WHEN CAST("_連番" AS INTEGER) = 1 THEN trim("馬名") END) AS sire,
                   max(CASE WHEN CAST("_連番" AS INTEGER) = 3 THEN trim("馬名") END) AS grandsire,
                   max(CASE WHEN CAST("_連番" AS INTEGER) = 5 THEN trim("馬名") END) AS damsire
            FROM {table}
            GROUP BY 1
        """).fetchdf()
