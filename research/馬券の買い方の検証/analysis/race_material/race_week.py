"""開催日から開催週の鍵を作る。"""

from __future__ import annotations

import pandas as pd

#: 週の始まりの曜日（土曜。``weekday()`` は月曜が 0）。
_SATURDAY = 5
_DAYS_IN_WEEK = 7


class RaceWeek:
    """開催日 → 開催週の鍵（その週の土曜日の ``YYYY-MM-DD``）。

    中央競馬は土日に開催し、祝日の月曜に振替の開催がある。土曜始まりにすると、土・日・月の開催が同じ週になる。
    """

    def key(self, day) -> str:
        """1日ぶん。"""
        return self.keys(pd.Series([pd.Timestamp(day)])).iloc[0]

    def keys(self, days: pd.Series) -> pd.Series:
        """開催日の列（日付）→ 週の鍵の列。"""
        dates = pd.to_datetime(days)
        offsets = (dates.dt.weekday - _SATURDAY) % _DAYS_IN_WEEK
        return (dates - pd.to_timedelta(offsets, unit="D")).dt.strftime("%Y-%m-%d")
