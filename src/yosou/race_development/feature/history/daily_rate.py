"""日ごとの数から、前日までの 365日の割合を出す。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import PEOPLE_WINDOW_DAYS, as_numbers
from yosou.shared.feature.history import AsOfLookup, DatedRecords

#: 日ごとの表で、誰の数かを表す列（共通の ``PeopleDayRepository`` の列）。
_PERSON_KEY = "person_code"


class DailyRate:
    """出走の行ごとに、その騎手の、開催日の前日までの 365日の「当たった数 ÷ 数えた数」を出す（設計書 09 の K）。

    共通の ``Top3Rate`` と同じ作り（日ごとの数を累計にし、前日までの累計 − 366日前までの累計）で、数える列を選べるようにしたもの。
    数えた数が ``min_count`` に満たなければ欠損値（少ない数の割合は当てにならないため）。平滑化はしない。
    """

    def __init__(self, entries: pd.DataFrame, entry_key: str, min_count: int) -> None:
        self._lookup = AsOfLookup(entries, entry_key)
        self._min_count = min_count

    def of(self, days: pd.DataFrame, hits_column: str, count_column: str) -> pd.Series:
        """``days`` は人ごと・開催日ごとの数（列 ``person_code``・``race_date``・``hits_column``・``count_column``）。"""
        ordered = days.sort_values([_PERSON_KEY, "race_date"], kind="stable").reset_index(drop=True)
        counts = pd.DataFrame({"hits": as_numbers(ordered[hits_column]), "count": as_numbers(ordered[count_column])})
        totals = counts.groupby(ordered[_PERSON_KEY], sort=False).cumsum()
        totals = totals.assign(**{_PERSON_KEY: ordered[_PERSON_KEY], "race_date": ordered["race_date"]})
        dated = DatedRecords(totals, _PERSON_KEY, "race_date")
        until_yesterday = self._lookup.latest(dated, days_before=1)
        before_window = self._lookup.latest(dated, days_before=PEOPLE_WINDOW_DAYS + 1)
        count = until_yesterday["count"].fillna(0) - before_window["count"].fillna(0)
        hits = until_yesterday["hits"].fillna(0) - before_window["hits"].fillna(0)
        return (hits / count).where(count >= self._min_count)
