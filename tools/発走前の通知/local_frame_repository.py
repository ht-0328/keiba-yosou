"""地方の元DB の出走馬の表（se）から、1レースの 馬番 → 枠番 を読む。"""

from __future__ import annotations

import duckdb

#: 1レースの出走馬の枠番（同じ馬番の行が複数あれば、データ区分・作成日の新しい行）。
_SQL = """
SELECT 馬番, 枠番
FROM se
WHERE 開催年 = ? AND 開催月日 = ? AND 競馬場コード = ? AND "開催回[第N回]" = ? AND "開催日目[N日目]" = ? AND レース番号 = ?
QUALIFY row_number() OVER (PARTITION BY 馬番 ORDER BY データ区分 DESC, データ作成年月日 DESC) = 1
"""


class LocalFrameRepository:
    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, rid: str) -> dict[int, int]:
        """``rid``（開催年 4・開催月日 4・競馬場 2・回 2・日目 2・レース番号 2）のレースの 馬番 → 枠番。枠番が無い馬は含めない。"""
        keys = (rid[:4], rid[4:8], rid[8:10], rid[10:12], rid[12:14], rid[14:16])
        rows = self._con.execute(_SQL, keys).fetchall()
        return {int(no): int(frame) for no, frame in rows if str(frame).strip().isdigit()}
