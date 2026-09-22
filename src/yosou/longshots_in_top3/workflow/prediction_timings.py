"""この予想が予測を出す時点（設計書 07）。"""

from __future__ import annotations

from yosou.shared.feature import PredictionTiming

#: この予想が学習し、予測を出す時点（木曜・前日・当日の3つ全部。利用者の決定）。木曜は人気を馬名で渡す。
TIMINGS: tuple[PredictionTiming, ...] = tuple(PredictionTiming)
#: 時点の書き方の案内（コマンドの説明に使う）。
TIMING_CHOICES = " / ".join(f"{timing.label}（{timing.value}）" for timing in TIMINGS)
