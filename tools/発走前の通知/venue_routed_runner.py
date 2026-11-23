"""レースの競馬場で、予想を動かす部品を振り分ける（ばんえいは専用の予想、ほかは地方の予想）。"""

from __future__ import annotations

from pathlib import Path

from 発走前の通知.day_notifier_protocols import Runner
from 発走前の通知.venue_route import is_banei


class VenueRoutedRunner:
    def __init__(self, local: Runner, banei: Runner) -> None:
        self._local = local
        self._banei = banei

    def run_day(self, day: str) -> None:
        self._local.run_day(day)
        self._banei.run_day(day)

    def run_race(self, rid: str, day: str) -> None:
        (self._banei if is_banei(rid) else self._local).run_race(rid, day)

    def log_path(self, day: str) -> Path:
        return self._local.log_path(day)
