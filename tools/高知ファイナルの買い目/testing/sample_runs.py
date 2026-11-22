"""テスト用の、架空の高知の出走の表（``RAW_COLUMNS`` の列）を作る。"""

from __future__ import annotations

import pandas as pd

from ..final_columns import RAW_COLUMNS

#: 架空の開催日の最初の日。
FIRST_DAY = pd.Timestamp("2025-01-05")
FINAL_NAME = "ファイナルレース"
HORSES = 10


class SampleRuns:
    """``days`` 日ぶん、1日 ``races`` レース・``HORSES`` 頭。同じ馬が毎日同じ番号のレースを走る（最後のレースが「ファイナルレース」）。
    着順は日ごとに1つずつずれる（馬番 + 日の番号 を頭数で割った余りの順）。値はどれも式で決まる架空のもの。"""

    def __init__(self, days: int = 6, races: int = 3) -> None:
        self._days = days
        self._races = races

    def rid(self, day_index: int, race_no: int) -> str:
        day = FIRST_DAY + pd.Timedelta(days=7 * day_index)
        return f"{day:%Y%m%d}540101{race_no:02d}"

    def build(self, unrun: str | None = None) -> pd.DataFrame:
        """全部の走。``unrun`` の rid のレースは、これから走るレース（着順・オッズなどの結果の列が欠損値）にする。"""
        rows = [self._row(day_index, race_no, horse_no) for day_index in range(self._days)
                for race_no in range(1, self._races + 1) for horse_no in range(1, HORSES + 1)]
        frame = pd.DataFrame(rows, columns=list(RAW_COLUMNS))
        if unrun is not None:
            results = ["finish", "corner4", "first_corner_rank", "time_diff", "finish_time", "last3f", "last3f_rank", "popularity", "win_odds"]
            frame.loc[frame["race_id"] == unrun, results] = None
        return frame

    def _row(self, day_index: int, race_no: int, horse_no: int) -> dict[str, object]:
        day = FIRST_DAY + pd.Timedelta(days=7 * day_index)
        finish = (horse_no + day_index + race_no) % HORSES + 1
        popularity = (horse_no + race_no) % HORSES + 1
        name = FINAL_NAME if race_no == self._races else f"一般{race_no}"
        return {"race_id": self.rid(day_index, race_no), "race_date": day, "race_no": race_no, "race_name": name,
                "horse_id": f"H{race_no}{horse_no:02d}", "horse_no": horse_no, "frame_no": (horse_no + 1) // 2, "field_size": HORSES, "ran": True,
                "finish": finish, "corner4": (finish + 1) % HORSES + 1, "first_corner_rank": (finish + 2) % HORSES + 1,
                "time_diff": 0.2 * (finish - 1), "finish_time": 90.0 + 0.2 * finish, "last3f": 39.0 + 0.1 * finish, "last3f_rank": finish,
                "popularity": popularity, "win_odds": 2.0 * popularity, "distance_m": 1400, "class_order": 3, "condition_order": 1,
                "carried": 56.0, "body_weight": 460 + horse_no, "weight_change": 0, "age": 4 + horse_no % 3, "sex": "牝" if horse_no % 2 else "牡",
                "interval_days": 7 if day_index else None, "jockey_code": f"J{(horse_no + day_index) % 5}", "trainer_code": f"T{horse_no % 4}",
                "jockey_change": "乗り替わり" if day_index else "前走なし", "prev_finish": None, "prev_popularity": None, "prev_time_diff": None,
                "prev_corner4": None, "runs_before": day_index, "wins_before": 0}
