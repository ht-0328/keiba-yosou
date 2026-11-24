"""成績の母数にする、全部のレース（買わなかったレースも含む）。"""

from __future__ import annotations

import pandas as pd

from 高配当の買い目.pick_columns import RACE_DATE, RACE_ID

#: 1年の日数（期間を年に直すのに使う）。
_DAYS_PER_YEAR = 365.25


class RaceUniverse:
    """全部のレース（1行 = 1レース。列 ``race_id``・``race_date``）。馬ごとの表（``RaceUniverseReader``）から作る。

    買い目の成績の「全レースに対する割合」「1開催日あたり」「1年あたり」の分母に使う。年ごとの予測のファイルにあるのは買う候補のあるレースだけなので、
    分母は予測のファイルのレースではなく、こちらを使う。
    例: 2020年1月5日〜2026年9月22日の表なら、``year_span`` は 6.71（年）。
    """

    def __init__(self, races: pd.DataFrame) -> None:
        unique = races.drop_duplicates(RACE_ID)
        self._races = unique.assign(**{RACE_DATE: pd.to_datetime(unique[RACE_DATE])})

    def of_years(self, years: set[int]) -> RaceUniverse:
        """開催日の年が ``years`` に入るレースだけ（年ごとの予測のある年にそろえる）。"""
        return RaceUniverse(self._races[self._races[RACE_DATE].dt.year.isin(years)])

    @property
    def race_count(self) -> int:
        return len(self._races)

    @property
    def day_count(self) -> int:
        """開催日の数。"""
        return int(self._races[RACE_DATE].nunique())

    @property
    def year_span(self) -> float:
        """最初の開催日から最後の開催日までの長さ（年）。レースが無ければ 0。"""
        if self._races.empty:
            return 0.0
        return (self._races[RACE_DATE].max() - self._races[RACE_DATE].min()).days / _DAYS_PER_YEAR

    def period_text(self) -> str:
        """例: ``2020-01-05 〜 2026-09-22``。レースが無ければ空。"""
        if self._races.empty:
            return ""
        return f"{self._races[RACE_DATE].min():%Y-%m-%d} 〜 {self._races[RACE_DATE].max():%Y-%m-%d}"
