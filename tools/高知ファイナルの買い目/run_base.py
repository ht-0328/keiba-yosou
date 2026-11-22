"""高知の出走の表に、1走ごとに決まる列（位置の割合・着順の旗・ファイナルレースの旗）を付ける。"""

from __future__ import annotations

import pandas as pd

from .repository.final_race_repository import FINAL_WORD

#: 数に直す列。
_NUMERIC: tuple[str, ...] = (
    "finish", "age", "frame_no", "horse_no", "field_size", "distance_m", "interval_days", "carried", "body_weight", "weight_change", "race_no",
    "prev_finish", "prev_popularity", "prev_corner4", "prev_time_diff", "runs_before", "wins_before", "class_order", "condition_order",
    "corner4", "first_corner_rank", "time_diff", "finish_time", "last3f", "last3f_rank", "popularity", "win_odds",
)


class RunBase:
    """出走した行だけを残し、馬 → 開催日 → レース番号の順に並べる。
    ``c4rel``・``c1rel`` は 4コーナー・最初のコーナーの位置（0 = 先頭、1 = 最後方）。``final`` はその日のいちばん後ろのレースで名前に
    「ファイナルレース」が入るレース。これから走るレースの行は着順が無いので、``top3``・``win`` は 0 になる（過去の材料には数えない）。"""

    def build(self, runs: pd.DataFrame) -> pd.DataFrame:
        d = runs[runs["ran"].fillna(False).astype(bool)].copy()
        d["race_id"] = d["race_id"].astype(str)
        d["race_date"] = pd.to_datetime(d["race_date"])
        for column in _NUMERIC:
            d[column] = pd.to_numeric(d[column], errors="coerce").astype(float)
        last_race = d.groupby("race_date")["race_no"].transform("max")
        d["final"] = d["race_name"].fillna("").str.contains(FINAL_WORD) & (d["race_no"] == last_race)
        d = d.sort_values(["horse_id", "race_date", "race_no"]).reset_index(drop=True)
        others = (d["field_size"] - 1).clip(lower=1)
        d["c4rel"] = (d["corner4"] - 1) / others
        d["c1rel"] = (d["first_corner_rank"] - 1) / others
        d["top3"] = (d["finish"] <= 3).astype(float)
        d["win"] = (d["finish"] == 1).astype(float)
        d["year"] = d["race_date"].dt.year
        return d
