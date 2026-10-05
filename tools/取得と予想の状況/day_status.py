"""中央の1開催日ぶんの、取得と予想の数え上げ。"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from 取得と予想の状況.acquisition_day import AcquisitionDay
from 取得と予想の状況.race_status import RaceStatus
from 取得と予想の状況.verdict_kind import VerdictKind


@dataclass(frozen=True)
class DayStatus:
    """中央の1開催日の、取得の数え上げ（``acquisition``）と、予想が何レースぶんあるか。数はすべてレース数。

    ``redo`` は予想し直すべきレース（時点が進んだ・作り方が古い・オッズが新しい）、``missing`` は未予想のレース。
    """

    acquisition: AcquisitionDay
    forecasted: int
    by_timing: dict[str, int] = field(default_factory=dict)
    fresh: int = 0
    redo: int = 0
    missing: int = 0

    @property
    def day(self) -> str:
        return self.acquisition.day

    @classmethod
    def summarize(cls, day: str, statuses: list[RaceStatus]) -> "DayStatus":
        """その日のレースの並びから数える。"""
        verdicts = [status.verdict for status in statuses]
        return cls(
            acquisition=AcquisitionDay.summarize(day, [status.signals for status in statuses]),
            forecasted=sum(verdict.is_saved for verdict in verdicts),
            by_timing=dict(Counter(verdict.saved_timing for verdict in verdicts if verdict.saved_timing)),
            fresh=sum(verdict.kind is VerdictKind.FRESH for verdict in verdicts),
            redo=sum(verdict.kind.needs_redo for verdict in verdicts),
            missing=sum(verdict.kind is VerdictKind.MISSING for verdict in verdicts),
        )

    def timing_text(self) -> str:
        """``前日 18・当日 12`` の形（時点の順）。"""
        return "・".join(f"{timing} {count}" for timing, count in self.by_timing.items())
