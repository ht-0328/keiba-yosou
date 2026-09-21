"""開催日の前 14日以内の調教を引く。"""

from __future__ import annotations

import pandas as pd

from ..time_windows import WORKOUT_WINDOW_DAYS
from .as_of_lookup import AsOfLookup
from .dated_records import DatedRecords

#: 馬ごとの、その調教までの本数（1から数える）を入れる列。
_DONE = "done"


class WorkoutLookup:
    """出走の行ごとに、開催日の前 14日以内（前日まで）の調教を引く。"""

    def __init__(self, entries: pd.DataFrame, workouts: pd.DataFrame) -> None:
        self._entries = entries
        self._lookup = AsOfLookup(entries, "horse_id")
        self._sessions = self._numbered(workouts)

    def latest(self) -> pd.DataFrame:
        """14日以内でいちばん新しい調教（コースを問わない）。無ければ、全部の列が欠損値。"""
        return self._latest_of(self._sessions)

    def latest_on(self, course: str) -> pd.DataFrame:
        """14日以内でいちばん新しい、``course``（坂路かウッド）の調教。無ければ、全部の列が欠損値。"""
        return self._latest_of(self._sessions[self._sessions["course"] == course])

    def count(self) -> pd.Series:
        """14日以内の調教の本数。「前日までの本数 − 15日前までの本数」で数える。"""
        until_yesterday = self._done_until(days_before=1)
        before_window = self._done_until(days_before=WORKOUT_WINDOW_DAYS + 1)
        return until_yesterday - before_window

    def _latest_of(self, sessions: pd.DataFrame) -> pd.DataFrame:
        found = self._lookup.latest(self._dated(sessions), days_before=1)
        window_first_day = self._entries["race_date"] - pd.Timedelta(days=WORKOUT_WINDOW_DAYS)
        return found.where(found["work_date"] >= window_first_day)

    def _done_until(self, days_before: int) -> pd.Series:
        found = self._lookup.latest(self._dated(self._sessions), days_before)
        return found[_DONE].fillna(0)

    def _numbered(self, workouts: pd.DataFrame) -> pd.DataFrame:
        """調教を馬・日時の古い順に並べ、馬ごとの通し番号を付ける。"""
        sessions = workouts.sort_values(["horse_id", "work_date", "work_time"], kind="stable")
        sessions = sessions.reset_index(drop=True)
        return sessions.assign(**{_DONE: sessions.groupby("horse_id", sort=False).cumcount() + 1})

    def _dated(self, sessions: pd.DataFrame) -> DatedRecords:
        return DatedRecords(sessions, key_column="horse_id", date_column="work_date")
