"""予測の流れを進める（オーケストレーション。設計書 05 の図2）。

ここのクラスは、ほかのフォルダのクラスを決まった順に呼んで、データを受け渡すだけ。計算・判断・SQL は書かない。

| 名前 | 仕事 |
|---|---|
| ``PredictionWorkflow`` | 予測の流れ。``PREDICTION_COLUMNS`` は結果の表の列の名前 |
| ``TIMINGS`` | この予想が学習し、予測を出す時点（木曜・前日・当日） |
| ``model_repositories()`` | 券種ごとのモデルの置き場所（``ModelRepository``）を作る関数 |

学習の流れ（``TrainingWorkflow``）は、どの予想でも同じなので ``yosou.shared.workflow``。券種ごとに回すのは
``command/`` の ``TrainCommand``。
"""

from .model_repositories import model_repositories
from .prediction_timings import TIMING_CHOICES, TIMINGS
from .prediction_workflow import BET, PREDICTION_COLUMNS, TOP_LEVEL, UPSET_OR_MORE, PredictionWorkflow

__all__ = [
    "PredictionWorkflow", "PREDICTION_COLUMNS", "BET", "TOP_LEVEL", "UPSET_OR_MORE",
    "TIMINGS", "TIMING_CHOICES", "model_repositories",
]
