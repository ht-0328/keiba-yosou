"""過去の傾きの表（同じ馬場 × 開催の何日目 × 馬場状態ごとの、過去のレースの傾きの平均）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from . import names


@dataclass(frozen=True)
class PriorSlopeTable:
    """過去の傾きの表。``cells`` は ``PRIOR_KEY`` ごとの縮めた傾き（``PRIOR_INNER``・``PRIOR_FRONT``）、``courses`` は同じ馬場
    （``COURSE_KEY``）ごとの傾き（マスの無い条件の寄せ先）、``as_of`` は使ったレースの最後の開催日（無ければ None）。"""

    cells: pd.DataFrame
    courses: pd.DataFrame
    as_of: date | None

    def lookup(self, races: pd.DataFrame) -> pd.DataFrame:
        """``races``（``PRIOR_KEY`` の列を持つ）の行ごとの過去の傾き（列 ``PRIOR_INNER``・``PRIOR_FRONT``。index は ``races`` と同じ）。
        マスが無ければ同じ馬場の値、それも無ければ 0（分からなければ偏りなしとみなす）。"""
        keys = races[list(names.PRIOR_KEY)].astype(str)
        by_cell = keys.merge(self.cells.astype({key: str for key in names.PRIOR_KEY}), on=list(names.PRIOR_KEY), how="left")
        by_course = keys.merge(self.courses.astype({key: str for key in names.COURSE_KEY}), on=list(names.COURSE_KEY), how="left")
        columns = [names.PRIOR_INNER, names.PRIOR_FRONT]
        found = by_cell[columns].fillna(by_course[columns]).fillna(0.0)
        return found.set_axis(races.index)
