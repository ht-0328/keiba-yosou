"""地方の元DB から読んだ1レースの行（rid・競馬場コード・R・レース名・発走時刻 HHMM）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LocalRaceRow:
    rid: str
    venue_code: str
    number: int
    name: str
    #: 発走時刻 HHMM（出馬表に無ければ空）。
    post: str
