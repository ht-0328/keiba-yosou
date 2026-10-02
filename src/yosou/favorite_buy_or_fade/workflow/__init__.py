"""流れを進める（オーケストレーション）クラス（設計書 05）。ほかのクラスを順に呼ぶだけ。

| クラス | 仕事 |
|---|---|
| ``TrainingDataReader`` | 元DB から、方針の「学習の最初の年」からの1番人気の学習データを読む |
| ``SimilarityTraining`` | 学習の流れ。時点の特徴量にする → 単位を決める → 単位ごとに3つのモデルを作る |
| ``FavoriteJudgement`` | 学習した一式で、1番人気ごとの単位・3つの近さ・判定を出す（評価と予測で同じもの） |
| ``YearlyEvaluation`` | 1年ごとに学習し直して、その年の1番人気を判定する |
| ``PredictionWorkflow`` | 予測の流れ。人気とオッズを決め、1レースの1番人気を判定する |
"""

from .favorite_judgement import FavoriteJudgement
from .prediction_workflow import PredictionWorkflow
from .similarity_training import SimilarityTraining
from .training_data_reader import TrainingDataReader
from .yearly_evaluation import YEAR, YearlyEvaluation

__all__ = [
    "TrainingDataReader", "SimilarityTraining", "FavoriteJudgement", "YearlyEvaluation", "YEAR", "PredictionWorkflow",
]
