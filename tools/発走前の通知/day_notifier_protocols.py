"""1日の流れ（DayNotifier）の部品のつなぎ目。

中央（RaceSchedule・StoreFetcher・ForecastRunner・RaceMessage・ForecastStore・Win5Job）と
地方（LocalRaceSchedule・StoreFetcher.local()・LocalForecastRunner・LocalRaceMessage・LocalForecastStore）を同じ流れで動かす。
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Protocol

from 発走前の通知.race_notice import RaceNotice
from 発走前の通知.scheduled_race import ScheduledRace
from 発走前の通知.win5_slot import Win5Slot


class Schedule(Protocol):
    def read(self, day: str) -> list[ScheduledRace]: ...


class Fetcher(Protocol):
    def sync(self) -> None: ...

    def fetch_day(self, day: str) -> None: ...

    def fetch_race(self, day: str, rid: str) -> None: ...


class Runner(Protocol):
    def run_day(self, day: str) -> None: ...

    def run_race(self, rid: str, day: str) -> None: ...

    def log_path(self, day: str) -> Path: ...


class Message(Protocol):
    def build(self, rid: str) -> RaceNotice: ...


class SavedAt(Protocol):
    def saved_at(self, rid: str) -> datetime | None: ...


class Poster(Protocol):
    def post(self, text: str, attachments: Sequence[Path] = ()) -> None: ...


class Win5(Protocol):
    """WIN5 の段（中央の ``Win5Job``）。``start`` は短い前の段（取り込みと元DB の写し）を済ませて、予想を裏で始める。
    ``finished`` は裏の予想が終わったか、``build`` は終わった予想から文を作る（失敗なら例外）、``cancel`` は裏の予想を止める。"""

    def slot(self, day: str) -> Win5Slot | None: ...

    def start(self, slot: Win5Slot) -> None: ...

    def finished(self) -> bool: ...

    def build(self, slot: Win5Slot) -> RaceNotice: ...

    def cancel(self) -> None: ...
