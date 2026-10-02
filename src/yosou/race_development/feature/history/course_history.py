"""コースごとの、過去のレースの記録のまとめ。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.feature import as_numbers

#: 数える日数（前日までの 1095日。設計書 09 の M）。
_WINDOW = "1095D"
#: コースの鍵（競馬場・コース・距離）。
_COURSE_KEY: tuple[str, ...] = ("venue_code", "track_code", "distance_m")
#: 出力の列（特徴量の名前。設計書 09 の M）。
FIRST_CORNER = "最初のコーナーの番号"
CORNER_COUNT = "記録されるコーナーの数"
LEADER_POSITION = "このコースで先頭になった馬の馬番の位置の平均"
_COLUMNS: tuple[str, ...] = (FIRST_CORNER, CORNER_COUNT, LEADER_POSITION)


class CourseHistory:
    """各レースに、同じコース（競馬場・コース・距離）の、開催日の前日までの 1095日のレースの記録のまとめを付ける（設計書 09 の M）。

    最初のコーナーの番号と記録されるコーナーの数は、真ん中の値（ほぼ一定なので、いちばん多いものと同じになる）。
    先頭になった馬の馬番の位置は、``先頭の馬番 ÷ 出走頭数`` の平均。コーナーを5回以上通るレースは数えない。
    同じ日のレースは数えない（設計書 11 の 7）。
    """

    def of(self, race_history: pd.DataFrame) -> pd.DataFrame:
        """列は ``_COLUMNS``、1行 = 1レース（index はレースID）。"""
        if race_history.empty:
            return pd.DataFrame(columns=list(_COLUMNS), dtype="float64")
        races = race_history.assign(race_date=pd.to_datetime(race_history["race_date"])).sort_values("race_date")
        usable = races["finished"].astype(bool) & ~races["corner_laps_over_one"].astype(bool)
        measures = pd.DataFrame({
            "first_corner": as_numbers(races["first_corner_no"]).where(usable),
            "corner_count": as_numbers(races["corner_count"]).where(usable),
            "leader": (as_numbers(races["first_corner_leader_no"]) / as_numbers(races["field_size"])).where(usable),
        })
        values = self._rolled(races, measures)
        return pd.DataFrame(values, columns=list(_COLUMNS), index=races["race_id"].to_numpy())

    def _rolled(self, races: pd.DataFrame, measures: pd.DataFrame) -> np.ndarray:
        """コースごとに、前日までの 1095日の真ん中の値（2つ）と平均（1つ）。"""
        days = races["race_date"].to_numpy()
        values = np.full((len(races), len(_COLUMNS)), np.nan)
        for rows in races.groupby(list(_COURSE_KEY), sort=False).indices.values():
            window = measures.iloc[rows].set_axis(days[rows]).rolling(_WINDOW, closed="left")
            median, mean = window.median(), window.mean()
            values[rows] = np.column_stack([median["first_corner"], median["corner_count"], mean["leader"]])
        return values
