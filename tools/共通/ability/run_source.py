"""能力指数の元になる、中央・平地の全出走を読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from .. import facts

#: 読む事実表の列（意味は ``facts.FACT_COLUMNS``）。
COLUMNS: tuple[str, ...] = (
    "race_id", "venue_code", "venue", "race_no", "track_code", "surface", "course", "distance_m", "condition",
    "class_name", "class_order", "field_size", "horse_id", "horse_no", "horse_name", "age", "sex", "carried",
    "finish", "finish_time", "style", "first3f", "last3f_race",
)


class RunSource:
    """事実表から、``first_day`` 以降の中央・平地の出走（出走した馬だけ。1行 = 1頭）を読む。

    ``relation`` を変えると、同じ列で別の表（``facts.build_entry_facts`` が作る、これから走るレースの出走馬）を読む。
    開催日・レースID・馬番の順に並べる。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, relation: str = facts.FACTS_TABLE) -> None:
        self._con = con
        self._relation = relation

    def read(self, first_day: date) -> pd.DataFrame:
        if self._relation == facts.FACTS_TABLE:
            facts.ensure_facts(self._con)
        sql = f"""
        SELECT {", ".join(COLUMNS)}, CAST(race_date AS DATE) AS race_date
        FROM {self._relation}
        WHERE ran AND surface IN ('芝', 'ダート') AND CAST(race_date AS DATE) >= ?
        ORDER BY race_date, race_id, horse_no
        """
        frame = self._con.execute(sql, [first_day.isoformat()]).df()
        return frame.assign(race_date=pd.to_datetime(frame["race_date"]))
