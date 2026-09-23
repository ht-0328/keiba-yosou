"""流れを進める（オーケストレーション）クラスのうち、どの予想でも同じもの。

| クラス | 仕事 |
|---|---|
| ``TrainingWorkflow`` | 学習の流れ（設計書 05 の図1）。時点ごとに2つのモデルを学習して保存する |
| ``ModelSegments`` | 学習データを区分（中穴・大穴、人気帯 など）に分けて、区分ごとに別のモデルで学ぶときの分け方 |
| ``SegmentedTraining`` | 区分ごとに ``TrainingWorkflow`` で学習して保存する（分けない予想は区分が「全体」1つ） |
| ``SegmentedPrediction`` | 予測用データの行を区分に分け、区分ごとのモデルで予測して、2つのモデルの確率と平均を返す |

予測の流れ（``PredictionWorkflow``）は、予想ごとに人気の扱いが違うので、ここには置かず、
予想のパッケージの ``workflow/`` に置く。
"""

from .model_segments import WHOLE, ModelSegments
from .segmented_prediction import AVERAGE, SegmentedPrediction
from .segmented_training import SegmentedTraining
from .training_workflow import TrainingWorkflow

__all__ = ["TrainingWorkflow", "ModelSegments", "WHOLE", "SegmentedTraining", "SegmentedPrediction", "AVERAGE"]
