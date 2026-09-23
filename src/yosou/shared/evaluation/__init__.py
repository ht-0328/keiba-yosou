"""学習したモデルの当たり具合を、学習に使っていないデータで測る。

二値分類（手本・人気馬・穴馬の予想。1行 = 1頭）は、確率の当たり具合を測る一般的な指標（ログ損失・AUC・Brier スコア）と、
「人気順をなぞるだけになっていないか」を見る指標（各レースで確率がいちばん高い馬と、人気がいちばん上の馬の、
目的変数が 1 だった割合と複勝の回収率。同じ人気の馬どうしで比べた AUC）を出す。1頭ごとの予想では、どれも同じ指標を使う。

多クラス分類（荒れ具合の予想。1行 = 1レース）は、正解率・マクロ F1・クラスのずれの平均・ログ損失・累積確率の AUC・
混同行列を出す（荒れ具合の設計書 16）。

| クラス | 仕事 |
|---|---|
| ``ModelEvaluator`` | 二値分類の、モデルごとと、アンサンブルの当たり具合を測る |
| ``MetricCalculator`` | 二値分類の予測確率と正解から、評価指標を計算する |
| ``Evaluation`` | 二値分類の、1つの時点・1つのモデルの当たり具合の値 |
| ``ClassModelEvaluator`` | 多クラス分類の、モデルごとと、アンサンブルの当たり具合を測る |
| ``ClassMetricCalculator`` | 多クラス分類のクラスごとの確率と正解から、評価指標を計算する |
| ``ClassEvaluation`` | 多クラス分類の、1つの時点・1つのモデルの当たり具合の値 |
| ``TrainingReport`` | 学習の結果の入れ物（使った期間・期間ごとのデータ・当たり具合・保存したフォルダ） |

``TrainingReport`` は、共通の ``workflow/`` の ``TrainingWorkflow`` が作り、``command/`` の ``TrainingReportTables``
（多クラス分類は ``ClassTrainingReportTables``）が表にする。
"""

from .class_evaluation import ClassEvaluation
from .class_metric_calculator import ClassMetricCalculator
from .class_model_evaluator import ClassModelEvaluator
from .evaluation import Evaluation
from .metric_calculator import MetricCalculator
from .model_evaluator import ENSEMBLE_NAME, ModelEvaluator
from .training_report import TrainingReport

__all__ = [
    "ModelEvaluator", "MetricCalculator", "Evaluation",
    "ClassModelEvaluator", "ClassMetricCalculator", "ClassEvaluation",
    "TrainingReport", "ENSEMBLE_NAME",
]
