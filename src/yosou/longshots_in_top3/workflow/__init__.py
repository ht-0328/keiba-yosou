"""予測の流れを進める（オーケストレーション。設計書 05 の図2）。

ここのクラスは、ほかのフォルダのクラスを決まった順に呼んで、データを受け渡すだけ。計算・判断・SQL は書かない。

| 名前 | 仕事 |
|---|---|
| ``PredictionWorkflow`` | 予測の流れ（設計書 05 の図2）。``PROBABILITY`` は確率の列の名前 |
| ``TIMINGS`` | この予想が学習し、予測を出す時点（木曜・前日・当日）。``TIMING_CHOICES`` はその書き方の案内 |

学習の流れ（``TrainingWorkflow``）は、どの予想でも同じなので ``yosou.shared.workflow``。人気と区分の扱いが
予想ごとに違う予測の流れだけを、ここに置く。学習の結果の入れ物（``TrainingReport``）は ``yosou.shared.evaluation``。
"""

from .prediction_timings import TIMING_CHOICES, TIMINGS
from .prediction_workflow import PROBABILITY, PredictionWorkflow

__all__ = ["PredictionWorkflow", "PROBABILITY", "TIMINGS", "TIMING_CHOICES"]
