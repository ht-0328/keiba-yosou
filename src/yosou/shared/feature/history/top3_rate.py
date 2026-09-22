"""近1年の3着以内の割合。"""

from __future__ import annotations

import pandas as pd

from ..time_windows import PEOPLE_WINDOW_DAYS
from ..value_types import as_numbers
from .as_of_lookup import AsOfLookup
from .dated_records import DatedRecords

#: 日ごとの成績の表で、誰（何）の成績かを表す列の既定の名前。
PERSON_KEY = "person_code"


class Top3Rate:
    """出走の行ごとに、その騎手（調教師・血統）の、開催日の前日までの 365日の3着以内の割合を出す。

    日ごとの成績を累計にしておき、「前日までの累計 − 366日前までの累計」で 365日分を数える。
    ``entry_key`` は出走の行の側の鍵の列、``history_key`` は日ごとの成績の表の側の鍵の列。
    """

    def __init__(self, entries: pd.DataFrame, entry_key: str, history_key: str = PERSON_KEY) -> None:
        self._lookup = AsOfLookup(entries, entry_key)
        self._history_key = history_key

    def of(self, days: pd.DataFrame) -> pd.Series:
        """``days`` は鍵ごと・開催日ごとの出走数と3着以内の数。期間に出走が無ければ欠損値。"""
        totals = DatedRecords(self._running_totals(days), self._history_key, "race_date")
        until_yesterday = self._lookup.latest(totals, days_before=1)
        before_window = self._lookup.latest(totals, days_before=PEOPLE_WINDOW_DAYS + 1)
        starts = until_yesterday["starts"].fillna(0) - before_window["starts"].fillna(0)
        places = until_yesterday["places"].fillna(0) - before_window["places"].fillna(0)
        return (places / starts).where(starts > 0)

    def _running_totals(self, days: pd.DataFrame) -> pd.DataFrame:
        """鍵ごとの、その日までの出走数と3着以内の数の累計。"""
        ordered = days.sort_values([self._history_key, "race_date"], kind="stable").reset_index(drop=True)
        counts = pd.DataFrame({
            "starts": as_numbers(ordered["starts"]),
            "places": as_numbers(ordered["places"]),
        })
        totals = counts.groupby(ordered[self._history_key], sort=False).cumsum()
        return totals.assign(**{self._history_key: ordered[self._history_key], "race_date": ordered["race_date"]})
