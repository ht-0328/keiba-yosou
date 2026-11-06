"""発走前の1レースの荒れ具合を出す入口と、予測を出す時点・置き場所の決めごと（設計書 04・07）。

予測の流れそのもの（``PredictionWorkflow``）と券種ごとのモデルの置き場所（``model_repositories``）は、中央の荒れ具合の予想と同じなので
``yosou.upset_level.workflow``。学習の流れ（``TrainingWorkflow``）は ``yosou.shared.workflow``。ここには、地方で増える入口と決めごとだけを置く。

| 名前 | 仕事 |
|---|---|
| ``LocalUpsetForecast`` | 1レースの U（当日の使う傾き）を出し、それを渡した ``RaceDatasetBuilder`` と中央の ``PredictionWorkflow`` で券種ごとの荒れ具合の確率を出す。``predict`` と、道具「地方の推奨買目」が使う |
| ``TIMINGS`` | この予想が学習し、予測を出す時点（出馬表・前日・当日の3つ全部） |
| ``TIMING_LABELS``・``TIMING_CHOICES`` | 時点 → 表に出す名前（共通の木曜の枠を「出馬表」と出す）と、コマンドの説明に使う書き方 |
| ``DEFAULT_MODELS_DIR``・``DEFAULT_CACHE_DIR`` | 学習したモデルと、学習データ・過去の傾きの表のとっておきの既定の置き場所（Git 対象外の reports/） |
"""

from .local_upset_forecast import LocalUpsetForecast
from .prediction_timings import DEFAULT_CACHE_DIR, DEFAULT_MODELS_DIR, TIMING_CHOICES, TIMING_LABELS, TIMINGS

__all__ = ["LocalUpsetForecast", "TIMINGS", "TIMING_LABELS", "TIMING_CHOICES", "DEFAULT_MODELS_DIR", "DEFAULT_CACHE_DIR"]
