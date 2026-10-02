"""単勝・複勝の払戻（1行 = 1つの払戻）を、払戻の子の表から直接読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

WIN, PLACE = "単勝", "複勝"

_SQL = f"""
SELECT "開催年" || "開催月日" || "競馬場コード" || "開催回[第N回]" || "開催日目[N日目]" || "レース番号" AS rid,
       TRY_CAST("馬番" AS INTEGER) AS horse_no, '{WIN}' AS kind, TRY_CAST("払戻金" AS BIGINT) AS yen
FROM "hr__単勝払戻"
UNION ALL
SELECT "開催年" || "開催月日" || "競馬場コード" || "開催回[第N回]" || "開催日目[N日目]" || "レース番号" AS rid,
       TRY_CAST("馬番" AS INTEGER) AS horse_no, '{PLACE}' AS kind, TRY_CAST("払戻金" AS BIGINT) AS yen
FROM "hr__複勝払戻"
"""


class PayoutRepository:
    """100円あたりの払戻（円）。同着のときは同じ券種に馬番が2つ以上並ぶ。空きの枠（馬番・払戻金が空）は読む側で落とす。"""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self) -> pd.DataFrame:
        """列は ``rid``・``horse_no``・``kind``（単勝・複勝）・``yen``。"""
        return self._con.execute(_SQL).fetchdf()
