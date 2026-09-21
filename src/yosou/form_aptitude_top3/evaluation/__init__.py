"""学習したモデルの当たり具合を、学習に使っていないデータで測る。

評価指標は設計書でまだ決まっていない（「次の設計書」）。いまは仮に、確率の当たり具合を測る一般的な指標
（ログ損失・AUC・Brier スコア）と、各レースで確率がいちばん高い馬の3着以内率を出す。

| クラス | 仕事 |
|---|---|
| ``ModelEvaluator`` | モデルごとと、アンサンブルの当たり具合を測る |
| ``MetricCalculator`` | 予測確率と正解から、評価指標を計算する |
| ``Evaluation`` | 1つの時点・1つのモデルの当たり具合の値 |
"""

from .evaluation import Evaluation
from .model_evaluator import ENSEMBLE_NAME, ModelEvaluator

__all__ = ["ModelEvaluator", "Evaluation", "ENSEMBLE_NAME"]
