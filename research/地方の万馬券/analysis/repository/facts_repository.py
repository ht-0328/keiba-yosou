"""事実表から、この研究が使う列の出走の行を読む（1 SQL）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import duckdb
import pandas as pd

from 共通.facts import FACTS_TABLE, ensure_facts

#: 読む列（事実表の列名）。結果側の列（finish・着差・通過順）は、事象を決めるためだけに使い、事情には使わない。
COLUMNS: tuple[str, ...] = (
    "race_id", "race_date", "year", "venue_code", "venue", "race_no", "race_name", "class_name", "class_order", "grade_code",
    "surface", "distance_m", "condition", "field_size", "frame_no", "horse_no", "horse_id", "sex", "age",
    "jockey_code", "trainer_code", "carried", "body_weight", "weight_change", "popularity", "win_odds",
    "finish", "time_diff", "corner4", "first_corner_rank", "win_payout", "place_payout",
    "prev_finish", "prev_popularity", "interval_days", "prev_time_diff", "prev_corner4", "prev_field_size",
    "prev_distance_m", "prev_venue", "class_change", "jockey_change", "venue_change", "distance_change",
    "runs_before", "wins_before", "course_runs_before", "best_time_unit_rank",
    "affiliation", "blinker", "apprentice", "mixed_sex",
)


@dataclass(frozen=True)
class FactsRepository:
    """``date_from`` 以降に出走した馬の行（事実表の ``ran`` が真のもの）。"""

    con: duckdb.DuckDBPyConnection

    def load(self, date_from: date) -> pd.DataFrame:
        ensure_facts(self.con)
        columns = ", ".join(COLUMNS)
        sql = f"SELECT {columns} FROM {FACTS_TABLE} WHERE ran AND race_date >= ? ORDER BY race_id, horse_no"
        return self.con.execute(sql, [date_from.isoformat()]).df()
