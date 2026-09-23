"""4つの予想モデルの当日時点の予測を、期間ぶん一括で出して CSV に残す。

| クラス | 仕事 |
|---|---|
| ``PredictionSource`` | 1モデルぶんの「学習データを作る工場」と「予測する部品の作り方」を束ねた値。``SOURCES`` が4モデルの一覧 |
| ``BatchPredictor`` | 期間の学習データから予測の表を作る決まり（インターフェース） |
| ``RunnerBatchPredictor`` | 1頭ごとの予想（近走と適性・人気馬・穴馬）の予測を、期間の全行に付ける |
| ``RaceBatchPredictor`` | レースの荒れ具合の予想の予測を、期間の全レース × 券種に付ける |
| ``UpsetProbabilityTable`` | 荒れ具合の4つの確率（行数 × 4）を、券種・固い〜超荒れ・いちばん高いクラス・中荒れ以上の確率 の表にする |
| ``PredictionFile`` | 予測の表を CSV に書き、読み戻す（レースID・馬ID は文字列のまま、開催日は日付） |
| ``PredictionManifest`` | 実行日時・期間・モデルの場所・行数を manifest.json に残す |
"""

from .batch_predictor import BatchPredictor
from .prediction_file import PredictionFile
from .prediction_manifest import MANIFEST_NAME, PredictionManifest
from .prediction_source import PredictionSource
from .prediction_sources import SOURCE_NAMES, SOURCES, source_named
from .race_batch_predictor import ACTUAL_LEVEL, RaceBatchPredictor
from .runner_batch_predictor import RunnerBatchPredictor
from .upset_probability_table import UpsetProbabilityTable

__all__ = [
    "PredictionSource", "SOURCES", "SOURCE_NAMES", "source_named", "BatchPredictor",
    "RunnerBatchPredictor", "RaceBatchPredictor", "ACTUAL_LEVEL", "UpsetProbabilityTable",
    "PredictionFile", "PredictionManifest", "MANIFEST_NAME",
]
