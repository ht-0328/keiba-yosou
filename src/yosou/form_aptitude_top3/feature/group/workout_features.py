"""I. 調教（6個）。"""

from __future__ import annotations

import pandas as pd

from ..entry_records import EntryRecords
from ..history import WorkoutLookup

#: 調教のコースの名前。坂路とウッドはタイムの意味が違うので、別の特徴量にする。
_HILL, _WOOD = "坂路", "ウッド"
#: 14日以内に調教が無いときの「直近の調教のコース」。
NO_WORKOUT = "なし"


class WorkoutFeatures:
    """I. 調教。開催日の前 14日以内の調教のうち、いちばん新しいものを「直近の調教」とする。"""

    def build(self, records: EntryRecords) -> pd.DataFrame:
        lookup = WorkoutLookup(records.entries, records.workouts)
        latest = lookup.latest()
        hill = lookup.latest_on(_HILL)
        wood = lookup.latest_on(_WOOD)
        return pd.DataFrame({
            "直近の調教のコース": latest["course"].fillna(NO_WORKOUT),
            "坂路の直近の4ハロンタイム": hill["four_furlongs"],
            "坂路の直近のラスト1ハロン": hill["last_furlong"],
            "ウッドの直近の4ハロンタイム": wood["four_furlongs"],
            "ウッドの直近のラスト1ハロン": wood["last_furlong"],
            "14日以内の調教の本数": lookup.count(),
        })
