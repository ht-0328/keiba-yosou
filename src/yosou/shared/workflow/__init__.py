"""流れを進める（オーケストレーション）クラスのうち、どの予想でも同じもの。

| クラス | 仕事 |
|---|---|
| ``TrainingWorkflow`` | 学習の流れ（設計書 05 の図1）。時点ごとに2つのモデルを学習して保存する |

予測の流れ（``PredictionWorkflow``）は、予想ごとに人気の扱いが違うので、ここには置かず、
予想のパッケージの ``workflow/`` に置く。
"""

from .training_workflow import TrainingWorkflow

__all__ = ["TrainingWorkflow"]
