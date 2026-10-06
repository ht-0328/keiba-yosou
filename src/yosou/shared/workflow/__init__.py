"""流れを進める（オーケストレーション）クラスのうち、どの予想でも同じもの。

| クラス | 仕事 |
|---|---|
| ``TrainingWorkflow`` | 学習の流れ（設計書 05 の図1）。時点ごとに2つのモデルを学習して保存する |
| ``ModelSegments`` | 学習データを区分（中穴・大穴、人気帯 など）に分けて、区分ごとに別のモデルで学ぶときの分け方 |
| ``SegmentedTraining`` | 区分ごとに ``TrainingWorkflow`` で学習して保存する（分けない予想は区分が「全体」1つ） |
| ``SegmentedPrediction`` | 予測用データの行を区分に分け、区分ごとのモデルで予測して、2つのモデルの確率と平均を返す |
| ``SegmentedHoldoutPrediction`` | 学習に使っていない期間の学習データを、区分ごとの保存したモデルで予測する |
| ``CalibrationCheck`` | 検証・テストの期間の馬を時点ごとに予測して、確率のずれを測る材料の表を作る |
| ``PredictionWorkflow`` | 1頭ごとの「3着以内」と「1着」の予想の予測の流れ（中央・地方の近走と適性の予想が使う。``PROBABILITY``・``WIN_PROBABILITY`` は確率の列の名前、``PaceSource`` は展開の予測を返す関数の型） |
| ``ExplainedPrediction`` | 予測の結果に、モデルに渡した特徴量の値と特徴量ごとの寄与を添えたもの（``PredictionWorkflow.explain``） |
| ``BacktestWorkflow`` | テスト期間の確かめの流れ（地方の設計書 05 の図4）。保存したモデルでテスト期間を予測し直し、市場の確率と比べ、道具「印の成績」が読む予測の表を書く |

人気の扱いが違う予想（穴馬・人気馬・荒れ具合）の予測の流れは、予想のパッケージの ``workflow/`` に置く。
"""

from .backtest_workflow import FIELD_SHARE_NAME, MARKET_NAME, BacktestWorkflow
from .calibration_check import CalibrationCheck
from .explained_prediction import ExplainedPrediction
from .model_segments import WHOLE, ModelSegments
from .prediction_workflow import PROBABILITY, WIN_PROBABILITY, PaceSource, PredictionWorkflow
from .segmented_holdout_prediction import SegmentedHoldoutPrediction
from .segmented_prediction import AVERAGE, SegmentedPrediction
from .segmented_training import SegmentedTraining
from .training_workflow import TrainingWorkflow

__all__ = [
    "TrainingWorkflow", "ModelSegments", "WHOLE", "SegmentedTraining", "SegmentedPrediction", "AVERAGE",
    "SegmentedHoldoutPrediction", "CalibrationCheck",
    "PredictionWorkflow", "ExplainedPrediction", "PROBABILITY", "WIN_PROBABILITY", "PaceSource",
    "BacktestWorkflow", "MARKET_NAME", "FIELD_SHARE_NAME",
]
