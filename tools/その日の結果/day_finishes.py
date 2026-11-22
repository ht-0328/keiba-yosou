"""1開催日の各レースの 1〜3着の馬番を元DB から読む。"""

from __future__ import annotations

from datetime import date

import duckdb

from 共通 import keys

#: 馬番ごとに新しい行（速報のあとに確定が届く）の、1〜3着。
_SQL = f"""
SELECT race_id, horse_no, finish FROM (
    SELECT {keys.rid_expr()} AS race_id, TRY_CAST(馬番 AS INTEGER) AS horse_no, TRY_CAST(確定着順 AS INTEGER) AS finish
    FROM se
    WHERE 開催年 = ? AND 開催月日 = ? AND {keys.jra_only()}
    {keys.latest_qualify((*keys.RACE_KEY, '馬番'))}
) WHERE finish BETWEEN 1 AND 3 ORDER BY race_id, finish, horse_no
"""


class DayFinishes:
    def read(self, con: duckdb.DuckDBPyConnection, day: date) -> dict[str, list[tuple[int, int]]]:
        """レース ID → （着順, 馬番）の並び（1〜3着。同着はそのまま並ぶ）。着順の届いていないレースは入らない。"""
        finishes: dict[str, list[tuple[int, int]]] = {}
        for race_id, horse_no, finish in con.execute(_SQL, [f"{day:%Y}", f"{day:%m%d}"]).fetchall():
            finishes.setdefault(str(race_id), []).append((int(finish), int(horse_no)))
        return finishes
