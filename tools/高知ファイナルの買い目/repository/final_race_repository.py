"""元DB のレース情報（ra）から、そのレースが高知のその日の最終レース「ファイナルレース」かを見る（SQL は1つ）。"""

from __future__ import annotations

import duckdb

#: 高知の競馬場コード。
KOCHI_CODE = "54"
#: レース名に入る言葉。
FINAL_WORD = "ファイナルレース"
#: その日の高知のレースの、いちばん大きいレース番号と、そのレースの名前（データ区分の新しい行）。
_SQL = """
SELECT レース番号, 競走名本題
FROM ra
WHERE 開催年 = ? AND 開催月日 = ? AND 競馬場コード = ?
QUALIFY row_number() OVER (PARTITION BY レース番号 ORDER BY データ区分 DESC, データ作成年月日 DESC) = 1
ORDER BY レース番号 DESC
LIMIT 1
"""


class FinalRaceRepository:
    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def is_final(self, rid: str) -> bool:
        """``rid``（16桁）が高知で、その日のいちばん後ろのレースで、名前に「ファイナルレース」が入っていれば真。"""
        if rid[8:10] != KOCHI_CODE:
            return False
        row = self._con.execute(_SQL, [rid[:4], rid[4:8], KOCHI_CODE]).fetchone()
        return bool(row) and str(row[0]) == rid[14:16] and FINAL_WORD in str(row[1] or "")
