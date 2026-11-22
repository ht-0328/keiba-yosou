"""元DB の出走馬の表（se）から、1レースの 馬番 → 騎手名（略称）を読む。中央と地方で同じ列。"""

from __future__ import annotations

import duckdb

#: 1レースの出走馬の騎手名の略称（同じ馬番の行が複数あれば、データ区分・作成日の新しい行。乗り替わりは新しい行に入る）。
_SQL = """
SELECT 馬番, 騎手名略称
FROM se
WHERE 開催年 = ? AND 開催月日 = ? AND 競馬場コード = ? AND "開催回[第N回]" = ? AND "開催日目[N日目]" = ? AND レース番号 = ?
QUALIFY row_number() OVER (PARTITION BY 馬番 ORDER BY データ区分 DESC, データ作成年月日 DESC) = 1
"""


class RaceJockeyRepository:
    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, rid: str) -> dict[int, str]:
        """``rid``（開催年 4・開催月日 4・競馬場 2・回 2・日目 2・レース番号 2）のレースの 馬番 → 騎手名の略称。騎手の無い馬は含めない。"""
        keys = (rid[:4], rid[4:8], rid[8:10], rid[10:12], rid[12:14], rid[14:16])
        rows = self._con.execute(_SQL, keys).fetchall()
        return {int(no): str(name).strip().replace("　", "") for no, name in rows
                if str(no).strip().isdigit() and str(name or "").strip()}
