"""この予想が予測を出す時点と、時点ごとに使うモデル（設計書 07）。"""

from __future__ import annotations

from yosou.shared.feature import PredictionTiming

#: この予想が学習し、予測を出す時点（木曜・前日・当日の3つ全部）。
TIMINGS: tuple[PredictionTiming, ...] = tuple(PredictionTiming)
#: 馬の力の材料に K を足したモデル（``ability_dataset_builder``）で予測する時点（手本と同じ）。
ABILITY_TIMINGS: tuple[PredictionTiming, ...] = (PredictionTiming.THURSDAY, PredictionTiming.DAY_BEFORE)
#: 当日の材料に K を足したモデル（``race_day_dataset_builder``）で予測する時点（当日）。
FORM_TIMINGS: tuple[PredictionTiming, ...] = tuple(timing for timing in TIMINGS if timing not in ABILITY_TIMINGS)
