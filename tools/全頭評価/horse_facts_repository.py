"""登録馬の行から、評価に使う事実を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from yosou.shared.repository import TargetScope

#: 読む列（事実表の列。意味は ``tools/共通/facts.py`` の ``FACT_COLUMNS``）。
COLUMNS: tuple[str, ...] = (
    "race_id", "race_date", "race_name", "venue", "surface", "course", "distance_m", "class_name", "grade_code",
    "horse_id", "horse_name", "sex", "age", "trainer", "affiliation", "sire", "damsire", "carried",
    "interval_days", "prev_finish", "prev_popularity", "prev_time_diff", "prev_last3f_rank", "prev_venue", "prev_distance_m",
    "prev_surface", "distance_change", "class_change", "surface_change",
    "runs_before", "wins_before", "lead_runs_before", "course_runs_before", "course_wins_before", "course_places_before",
    "same_race_runs_before", "same_race_wins_before", "same_race_places_before", "venue_wins_before", "dist_wins_before",
    "style_before",
)


class HorseFactsRepository:
    """登録馬の行の一時表（事実表と同じ列）から、評価の文に使う事実を読む（1 SQL）。1行 = 1頭。"""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, scope: TargetScope) -> pd.DataFrame:
        """列は ``COLUMNS``。``race_date`` は日付型、``horse_id`` は文字列。馬ID の順。"""
        sql = f"SELECT {', '.join(COLUMNS)} FROM {scope.relation} ORDER BY horse_id"
        frame = self._con.execute(sql).df()
        return frame.assign(race_date=pd.to_datetime(frame["race_date"]), horse_id=frame["horse_id"].astype(str))
