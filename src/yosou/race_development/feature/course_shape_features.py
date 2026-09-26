"""M. コースの形（3個）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import EntryRecords

from .history import CourseHistory


class CourseShapeFeatures:
    """M. このコースで、どの位置の馬が前に行きやすいか（設計書 09 の M）。``FeatureGroup`` を守る。

    コースの形の表はまだ無いので、過去のレースの記録（``race_history``）から作る（設計書 15 の 8）。
    同じレースの馬は、みな同じ値になる。
    """

    def __init__(self) -> None:
        self._course_history = CourseHistory()

    def build(self, records: EntryRecords) -> pd.DataFrame:
        by_race = self._course_history.of(records.race_history)
        found = by_race.reindex(records.entries["race_id"].to_numpy())
        return found.set_axis(records.entries.index)
