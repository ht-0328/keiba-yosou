"""I. 調教（6個）。"""

from __future__ import annotations

import pandas as pd

from ..entry_records import EntryRecords
from ..history import HILL, WOOD, WorkoutLookup

#: 14日以内に調教が無いときの「直近の調教のコース」。
NO_WORKOUT = "なし"


class WorkoutFeatures:
    """I. 調教。開催日の前 14日以内の調教のうち、いちばん新しいものを「直近の調教」とする。

    記録が DB に無い期間（ウッドは 2021年7月27日より前）の出走は、そのコースが関わる特徴量を欠損値（不明）に
    する。「調教が無い」（なし・0）と「記録が無い」（欠損値）を、モデルが取り違えないようにするためである。
    """

    def build(self, records: EntryRecords) -> pd.DataFrame:
        lookup = WorkoutLookup(records.entries, records.workouts)
        hill_known = records.workout_coverage.covers(records.entries, HILL)
        wood_known = records.workout_coverage.covers(records.entries, WOOD)
        both_known = hill_known & wood_known
        latest = lookup.latest()
        hill = lookup.latest_on(HILL)
        wood = lookup.latest_on(WOOD)
        return pd.DataFrame({
            "直近の調教のコース": latest["course"].fillna(NO_WORKOUT).where(both_known),
            "坂路の直近の4ハロンタイム": hill["four_furlongs"].where(hill_known),
            "坂路の直近のラスト1ハロン": hill["last_furlong"].where(hill_known),
            "ウッドの直近の4ハロンタイム": wood["four_furlongs"].where(wood_known),
            "ウッドの直近のラスト1ハロン": wood["last_furlong"].where(wood_known),
            "14日以内の調教の本数": lookup.count().where(both_known),
        })
