"""事実表から、この研究が使う列の出走の行を読む（1 SQL）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import duckdb
import pandas as pd

from 共通.facts import FACTS_TABLE, ensure_facts

#: 読む列（事実表の列名）。結果側の列（着順・通過順・上がり・前後半のタイム）は、事例を決めることと理解のための表にだけ使う。
COLUMNS: tuple[str, ...] = (
    "race_id", "race_date", "year", "venue", "race_no", "race_name", "surface", "course", "distance_m", "condition",
    "class_name", "class_order", "weight_type", "field_size", "frame_no", "horse_no", "horse_id", "horse_name",
    "jockey", "carried", "body_weight", "popularity", "win_odds", "finish", "time_diff",
    "corner1", "corner2", "corner3", "corner4", "first_corner_rank", "last3f_rank", "style", "first3f", "last3f_race",
    "prev_finish", "prev_popularity", "class_change", "runs_before", "course_runs_before", "course_places_before",
    "dist_wins_before", "cond_places_before", "apprentice", "style_before", "lead_candidates",
)

#: 数にしておく列（事実表では欠けを持てる整数の型なので、計算しやすい小数にそろえる）。
NUMERIC: tuple[str, ...] = (
    "year", "race_no", "distance_m", "class_order", "field_size", "frame_no", "horse_no", "carried", "body_weight",
    "popularity", "win_odds", "finish", "time_diff", "corner1", "corner2", "corner3", "corner4", "first_corner_rank",
    "last3f_rank", "first3f", "last3f_race", "prev_finish", "prev_popularity", "runs_before", "course_runs_before",
    "course_places_before", "dist_wins_before", "cond_places_before", "lead_candidates",
)


@dataclass(frozen=True)
class RunnerFactsRepository:
    """``date_from`` 以降に中央の平地で出走した馬の行（事実表の ``ran`` が真のもの。障害は除く）。"""

    con: duckdb.DuckDBPyConnection

    def load(self, date_from: date) -> pd.DataFrame:
        ensure_facts(self.con)
        columns = ", ".join(COLUMNS)
        sql = (f"SELECT {columns} FROM {FACTS_TABLE} WHERE ran AND surface <> '障害' AND race_date >= ? "
               "ORDER BY race_id, horse_no")
        frame = self.con.execute(sql, [date_from.isoformat()]).df()
        return frame.astype({column: "float64" for column in NUMERIC})
