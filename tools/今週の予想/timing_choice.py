"""1レースに使う時点と、その理由。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.shared.feature import PredictionTiming


@dataclass(frozen=True)
class TimingChoice:
    """選んだ時点と、その理由（画面に出す1文）。"""

    timing: PredictionTiming
    reason: str
