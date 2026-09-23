"""事実表から、レースの属性を期間ぶん読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts

from .race_day_range import RaceDayRange

#: 出力の列（事実表の列名のまま）。
RACE_COLUMNS: tuple[str, ...] = (
    "race_id", "race_date", "venue_code", "race_no", "surface", "distance_m", "class_order", "grade_code", "field_size",
)


class RaceFactRepository:
    """事実表（``tools/共通/facts.py``。1行 = 1頭）から、期間のレースの属性を 1レース1行で読む。

    重賞かどうかは ``grade_code``（A G1・B G2・C G3・D 重賞）で決める。事実表が無ければ作る（接続ごとに1回、約20秒）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, days: RaceDayRange) -> pd.DataFrame:
        facts.ensure_facts(self._con)
        sql = f"""
        SELECT race_id, min(CAST(race_date AS DATE)) AS race_date, any_value(venue_code) AS venue_code,
               any_value(race_no) AS race_no, any_value(surface) AS surface, any_value(distance_m) AS distance_m,
               any_value(class_order) AS class_order, any_value(grade_code) AS grade_code, any_value(field_size) AS field_size
        FROM {facts.FACTS_TABLE}
        WHERE CAST(race_date AS DATE) BETWEEN ? AND ?
        GROUP BY race_id
        ORDER BY race_date, race_id
        """
        return self._con.execute(sql, [days.first_day, days.last_day]).df()
