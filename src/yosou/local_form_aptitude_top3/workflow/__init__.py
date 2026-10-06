"""予測を出す時点と、モデルの置き場所の決めごと（設計書 07）。

予測の流れ（``PredictionWorkflow``）・学習の流れ（``TrainingWorkflow``）・テスト期間の確かめの流れ（``BacktestWorkflow``）は、
中央の予想と同じなので ``yosou.shared.workflow``。ここには、この予想の時点の呼び名と置き場所だけを置く。

| 名前 | 仕事 |
|---|---|
| ``TIMINGS`` | この予想が学習し、予測を出す時点（出馬表・前日・当日の3つ全部） |
| ``TIMING_LABELS`` | 時点 → 表に出す名前（共通の木曜の枠を「出馬表」と出す） |
| ``POOL_FREE_FOLDER`` | 当日に券種のオッズが無いときに使う、N を使わないモデルの置き場所（フォルダの名前） |
| ``WIN_FOLDER`` | 1着のモデル（目的変数「1着」）の置き場所（フォルダの名前） |
| ``DEFAULT_PREDICTIONS_DIR`` | テスト期間の確かめの予測の表の既定の置き場所 |
"""

from .prediction_timings import DEFAULT_PREDICTIONS_DIR, POOL_FREE_FOLDER, TIMING_LABELS, TIMINGS, WIN_FOLDER

__all__ = ["TIMINGS", "TIMING_LABELS", "POOL_FREE_FOLDER", "WIN_FOLDER", "DEFAULT_PREDICTIONS_DIR"]
