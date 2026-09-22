"""この予想が予測を出す時点（設計書 07）。"""

from __future__ import annotations

from yosou.shared.feature import PredictionTiming

#: この予想が学習し、予測を出す時点（木曜・前日・当日の3つ全部）。
TIMINGS: tuple[PredictionTiming, ...] = tuple(PredictionTiming)
