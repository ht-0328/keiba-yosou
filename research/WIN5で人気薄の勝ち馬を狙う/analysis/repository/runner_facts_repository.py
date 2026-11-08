"""事実表から、この研究が使う列の出走の行を読む（1 SQL）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import duckdb
import pandas as pd

from 共通.facts import FACTS_TABLE, ensure_facts

#: 読む列（事実表の列名）。結果側の列（finish・通過順・上がり・前後半のタイム）は、事象を決めることと、理解のための表にだけ使う。
COLUMNS: tuple[str, ...] = (
    "race_id", "race_date", "year", "month", "venue", "race_no", "race_name", "surface", "course", "distance_m",
    "condition", "class_name", "class_order", "grade_code", "weight_type", "field_size", "mixed_age",
    "frame_no", "horse_no", "horse_id", "horse_name", "sex", "age", "jockey_code", "trainer_code", "carried", "body_weight", "weight_change",
    "popularity", "win_odds", "finish", "time_diff", "corner4", "last3f_rank", "style", "first3f", "last3f_race",
    "sire", "damsire", "prev_finish", "prev_popularity", "interval_days", "prev_time_diff", "prev_corner4", "prev_field_size",
    "prev_distance_m", "prev_surface", "prev_venue", "surface_change", "distance_change", "class_change", "jockey_change",
    "runs_before", "wins_before", "course_runs_before", "course_wins_before", "course_places_before", "venue_wins_before",
    "dist_wins_before", "cond_places_before", "best_time_unit_rank", "best_time_dist_rank", "blinker", "apprentice",
    "style_before", "lead_candidates", "dm_rank", "tm_rank",
)

#: 数にしておく列（事実表では欠けを持てる整数の型なので、計算しやすい小数にそろえる）。
NUMERIC: tuple[str, ...] = (
    "year", "month", "race_no", "distance_m", "class_order", "field_size", "frame_no", "horse_no", "age", "carried",
    "body_weight", "weight_change", "popularity", "win_odds", "finish", "time_diff", "corner4", "last3f_rank", "first3f",
    "last3f_race", "prev_finish", "prev_popularity", "interval_days", "prev_time_diff", "prev_corner4", "prev_field_size",
    "prev_distance_m", "runs_before", "wins_before", "course_runs_before", "course_wins_before", "course_places_before",
    "venue_wins_before", "dist_wins_before", "cond_places_before", "best_time_unit_rank", "best_time_dist_rank",
    "lead_candidates", "dm_rank", "tm_rank",
)


@dataclass(frozen=True)
class RunnerFactsRepository:
    """``date_from`` 以降に中央で出走した馬の行（事実表の ``ran`` が真のもの。障害も含む。過去走をたどるのに使う）。"""

    con: duckdb.DuckDBPyConnection

    def load(self, date_from: date) -> pd.DataFrame:
        ensure_facts(self.con)
        columns = ", ".join(COLUMNS)
        sql = f"SELECT {columns} FROM {FACTS_TABLE} WHERE ran AND race_date >= ? ORDER BY race_id, horse_no"
        frame = self.con.execute(sql, [date_from.isoformat()]).df()
        return frame.astype({column: "float64" for column in NUMERIC})
