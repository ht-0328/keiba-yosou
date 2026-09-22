"""この予想が予測を出す時点（設計書 07）。"""

from __future__ import annotations

from yosou.shared.feature import PredictionTiming

#: この予想が学習し、予測を出す時点（前日・当日）。木曜は、馬番も人気も決まっていないので出さない。
TIMINGS: tuple[PredictionTiming, ...] = (PredictionTiming.DAY_BEFORE, PredictionTiming.RACE_DAY)
#: 時点の書き方の案内（コマンドの説明と、誤りの文面に使う）。
TIMING_CHOICES = " / ".join(f"{timing.label}（{timing.value}）" for timing in TIMINGS)
