"""調教の記録が DB にある期間。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

import pandas as pd

from ..time_windows import WORKOUT_WINDOW_DAYS

#: 調教のコースの名前。坂路とウッドはタイムの意味が違うので、別の特徴量にする。
HILL, WOOD = "坂路", "ウッド"
COURSES: tuple[str, ...] = (HILL, WOOD)
#: 「全期間に記録がある」の代わりの日（中央競馬の記録より前）。手で作った記録のテストに使う。
_ALWAYS = date(1900, 1, 1)


@dataclass(frozen=True)
class WorkoutCoverage:
    """調教のコースごとの、DB にある記録の最初の日。

    JRA-VAN のウッドチップ調教は 2021年7月27日から提供が始まった。それより前の出走は、ウッドで調教して
    いないのではなく、記録そのものが無い。この2つを取り違えないよう、開催日の前 14日の窓が記録のある
    期間に収まらない出走は、そのコースの調教を「不明」（欠損値）にする（設計書 09 の I）。
    """

    first_days: Mapping[str, date]

    @classmethod
    def from_table(cls, table: pd.DataFrame) -> WorkoutCoverage:
        """``WorkoutCoverageRepository`` が読んだ表（列 ``course``・``first_day``）から作る。日が読めない行は無視する。"""
        first_days = {
            row.course: pd.Timestamp(row.first_day).date()
            for row in table.itertuples() if pd.notna(row.first_day)
        }
        return cls(first_days)

    @classmethod
    def complete(cls) -> WorkoutCoverage:
        """全部のコースに、全期間の記録があるとみなす。"""
        return cls({course: _ALWAYS for course in COURSES})

    def covers(self, entries: pd.DataFrame, course: str) -> pd.Series:
        """出走の行ごとに、開催日の前 14日の窓の全部が、``course`` の記録のある期間に入っているか。

        記録が1本も無いコースは、どの出走でも False。
        """
        first_day = self.first_days.get(course)
        if first_day is None:
            return pd.Series(False, index=entries.index)
        window_first_day = entries["race_date"] - pd.Timedelta(days=WORKOUT_WINDOW_DAYS)
        return window_first_day >= pd.Timestamp(first_day)
