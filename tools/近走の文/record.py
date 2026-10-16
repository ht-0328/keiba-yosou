"""走の束の着別度数。"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .past_run import PastRun


@dataclass(frozen=True)
class Record:
    """着別度数（1着・2着・3着・着外の数）。``text`` は ``1-2-3-4`` の形、``place_rate`` は3着以内率（走が無ければ 0）。"""

    first: int
    second: int
    third: int
    out: int

    @classmethod
    def of(cls, runs: Iterable[PastRun]) -> "Record":
        """着順の付いた走だけ数える（中止などで着順の無い走は数えない）。"""
        counts = [0, 0, 0, 0]
        for run in runs:
            if run.finish is None:
                continue
            counts[min(run.finish, 4) - 1] += 1
        return cls(*counts)

    @property
    def count(self) -> int:
        return self.first + self.second + self.third + self.out

    @property
    def place_rate(self) -> float:
        return (self.first + self.second + self.third) / self.count if self.count else 0.0

    @property
    def text(self) -> str:
        return f"{self.first}-{self.second}-{self.third}-{self.out}"
