"""学習したモデルの当たり具合を、学習に使っていないデータで測る（穴馬の設計書 16）。

確率の当たり具合を測る一般的な指標（ログ損失・AUC・Brier スコア）と、「人気順をなぞるだけになっていないか」を
見る指標（各レースで確率がいちばん高い馬と、人気がいちばん上の馬の、目的変数が 1 だった割合と複勝の回収率。
同じ人気の馬どうしで比べた AUC）を出す。どの予想でも同じ指標を使う。

| クラス | 仕事 |
|---|---|
| ``ModelEvaluator`` | モデルごとと、アンサンブルの当たり具合を測る |
| ``MetricCalculator`` | 予測確率と正解から、評価指標を計算する |
| ``Evaluation`` | 1つの時点・1つのモデルの当たり具合の値 |
| ``TrainingReport`` | 学習の結果の入れ物（使った期間・期間ごとのデータ・当たり具合・保存したフォルダ） |

``TrainingReport`` は、共通の ``workflow/`` の ``TrainingWorkflow`` が作り、``command/`` の ``TrainingReportTables`` が表にする。
"""

from .evaluation import Evaluation
from .model_evaluator import ENSEMBLE_NAME, ModelEvaluator
from .training_report import TrainingReport

__all__ = ["ModelEvaluator", "Evaluation", "TrainingReport", "ENSEMBLE_NAME"]
