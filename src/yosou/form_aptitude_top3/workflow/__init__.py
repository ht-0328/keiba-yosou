"""予測の流れを進める（オーケストレーション。設計書 05 の図2）。

ここのクラスは、ほかのフォルダのクラスを決まった順に呼んで、データを受け渡すだけ。計算・判断・SQL は書かない。

| 名前 | 仕事 |
|---|---|
| ``PredictionWorkflow`` | 予測の流れ（設計書 05 の図2）。地方の予想と同じなので ``yosou.shared.workflow`` にあり、ここから同じ名前で使える。``PROBABILITY``・``WIN_PROBABILITY`` は確率の列の名前、``PaceSource`` は展開の予測を返す関数の型、``DataAttachment`` は予測用データに列を足す関数の型 |
| ``ExplainedPrediction`` | 予測の結果に、モデルに渡した特徴量の値と特徴量ごとの寄与（理由を見せる材料）を添えたもの（``PredictionWorkflow.explain``。同じく ``yosou.shared.workflow``） |
| ``TIMINGS`` | この予想が学習し、予測を出す時点（木曜・前日・当日） |
| ``ABILITY_TIMINGS``・``FORM_TIMINGS`` | 馬の力の材料のモデルで予測する時点と、今の材料のモデルで予測する時点 |
| ``PACE_TIMINGS`` | 展開の予想の結果（P）を足して学ぶ時点（木曜） |
| ``SCORE_TOP3_TIMINGS``・``SCORE_WIN_TIMINGS``・``SCORE_TIMINGS`` | 展開スコア（S）を足して学ぶ時点（3着以内のモデル・1着のモデル・そのどちらか） |
| ``ABILITY_SCORE_TOP3_TIMINGS``・``ABILITY_SCORE_WIN_TIMINGS``・``ABILITY_SCORE_TIMINGS`` | 能力スコア（T）を足して学ぶ時点（同じく） |
| ``TRACK_BIAS_TOP3_TIMINGS``・``TRACK_BIAS_WIN_TIMINGS``・``TRACK_BIAS_TIMINGS`` | トラックバイアスの補正（U）を足して学ぶ時点（同じく） |
| ``WEIGHT_DISCOUNT_TOP3_TIMINGS``・``WEIGHT_DISCOUNT_WIN_TIMINGS``・``WEIGHT_DISCOUNT_TIMINGS`` | 馬体重の表の割引（V）を足して学ぶ時点（同じく） |
| ``POOL_FREE_FOLDER`` | 当日に券種のオッズが無いときに使う、N を使わないモデルの置き場所（フォルダの名前） |
| ``WIN_FOLDER`` | 1着のモデル（目的変数「1着」）の置き場所（フォルダの名前） |

学習の流れ（``TrainingWorkflow``）は、どの予想でも同じなので ``yosou.shared.workflow``。
学習の結果の入れ物（``TrainingReport``）は ``yosou.shared.evaluation``。
"""

from yosou.shared.workflow import PROBABILITY, WIN_PROBABILITY, DataAttachment, ExplainedPrediction, PaceSource, PredictionWorkflow

from .prediction_timings import (
    ABILITY_SCORE_TIMINGS,
    ABILITY_SCORE_TOP3_TIMINGS,
    ABILITY_SCORE_WIN_TIMINGS,
    ABILITY_TIMINGS,
    FORM_TIMINGS,
    PACE_TIMINGS,
    POOL_FREE_FOLDER,
    SCORE_TIMINGS,
    SCORE_TOP3_TIMINGS,
    SCORE_WIN_TIMINGS,
    TIMINGS,
    TRACK_BIAS_TIMINGS,
    TRACK_BIAS_TOP3_TIMINGS,
    TRACK_BIAS_WIN_TIMINGS,
    WEIGHT_DISCOUNT_TIMINGS,
    WEIGHT_DISCOUNT_TOP3_TIMINGS,
    WEIGHT_DISCOUNT_WIN_TIMINGS,
    WIN_FOLDER,
)

__all__ = ["PredictionWorkflow", "ExplainedPrediction", "PROBABILITY", "WIN_PROBABILITY", "PaceSource", "DataAttachment", "TIMINGS", "ABILITY_TIMINGS",
           "FORM_TIMINGS", "PACE_TIMINGS", "SCORE_TIMINGS", "SCORE_TOP3_TIMINGS", "SCORE_WIN_TIMINGS",
           "ABILITY_SCORE_TIMINGS", "ABILITY_SCORE_TOP3_TIMINGS", "ABILITY_SCORE_WIN_TIMINGS",
           "TRACK_BIAS_TIMINGS", "TRACK_BIAS_TOP3_TIMINGS", "TRACK_BIAS_WIN_TIMINGS",
           "WEIGHT_DISCOUNT_TIMINGS", "WEIGHT_DISCOUNT_TOP3_TIMINGS", "WEIGHT_DISCOUNT_WIN_TIMINGS", "POOL_FREE_FOLDER", "WIN_FOLDER"]
