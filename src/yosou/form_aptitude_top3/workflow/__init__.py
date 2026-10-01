"""予測の流れを進める（オーケストレーション。設計書 05 の図2）。

ここのクラスは、ほかのフォルダのクラスを決まった順に呼んで、データを受け渡すだけ。計算・判断・SQL は書かない。

| 名前 | 仕事 |
|---|---|
| ``PredictionWorkflow`` | 予測の流れ（設計書 05 の図2）。``PROBABILITY`` は確率の列の名前 |
| ``TIMINGS`` | この予想が学習し、予測を出す時点（木曜・前日・当日） |
| ``ABILITY_TIMINGS``・``FORM_TIMINGS`` | 馬の力の材料のモデルで予測する時点と、今の材料のモデルで予測する時点 |
| ``POOL_FREE_FOLDER`` | 当日に券種のオッズが無いときに使う、N を使わないモデルの置き場所（フォルダの名前） |

学習の流れ（``TrainingWorkflow``）は、どの予想でも同じなので ``yosou.shared.workflow``。
学習の結果の入れ物（``TrainingReport``）は ``yosou.shared.evaluation``。
"""

from .prediction_timings import ABILITY_TIMINGS, FORM_TIMINGS, POOL_FREE_FOLDER, TIMINGS
from .prediction_workflow import PROBABILITY, PredictionWorkflow

__all__ = ["PredictionWorkflow", "PROBABILITY", "TIMINGS", "ABILITY_TIMINGS", "FORM_TIMINGS", "POOL_FREE_FOLDER"]
