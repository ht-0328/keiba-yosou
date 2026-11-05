"""地方の元DB（nvdata-store）のレース情報（ra）から、その日の地方のレースを読む（SQL は1つ）。"""

from __future__ import annotations

import duckdb

from 共通.local_codes import LOCAL_VENUE_RANGE

from 発走前の通知.local_race_row import LocalRaceRow

#: 同じレースの行が複数あれば（出馬表 → 成績）、データ区分の新しい方だけ。ばんえい（83）は地方の範囲（30〜61）に入らない。
_SQL = """
SELECT 開催年 || 開催月日 || 競馬場コード || "開催回[第N回]" || "開催日目[N日目]" || レース番号 AS rid,
       競馬場コード, レース番号, 競走名本題, 発走時刻
FROM ra
WHERE 開催年 = ? AND 開催月日 = ? AND 競馬場コード BETWEEN ? AND ?
QUALIFY row_number() OVER (PARTITION BY rid ORDER BY データ区分 DESC, データ作成年月日 DESC) = 1
ORDER BY 発走時刻, rid
"""


class LocalRaceRepository:
    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, day: str) -> list[LocalRaceRow]:
        """``day``（YYYY-MM-DD）の地方のレースを発走時刻の順に。"""
        year, monthday = day[:4], day[5:7] + day[8:10]
        rows = self._con.execute(_SQL, [year, monthday, *LOCAL_VENUE_RANGE]).fetchall()
        return [LocalRaceRow(rid=str(rid), venue_code=str(venue), number=int(number), name=str(name or "").strip(), post=str(post or "").strip())
                for rid, venue, number, name, post in rows]
