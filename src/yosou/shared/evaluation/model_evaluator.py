"""モデルごとと、アンサンブルの当たり具合を測る。"""

from __future__ import annotations

from ..dataset import TrainingData
from ..feature import PredictionTiming
from ..ml_model import EnsembleModel
from .evaluation import Evaluation
from .metric_calculator import MetricCalculator

#: アンサンブルの行に出すモデルの名前。
ENSEMBLE_NAME = "平均（アンサンブル）"


class ModelEvaluator:
    """1つの時点のモデル（LightGBM・CatBoost）と、その平均の当たり具合を測る。"""

    def evaluate(self, timing: PredictionTiming, ensemble: EnsembleModel,
                 data: TrainingData) -> list[Evaluation]:
        """``data`` は学習に使っていないデータ。モデルごとの行と、アンサンブルの行を返す。"""
        timed = data.for_timing(timing)
        member_probabilities = ensemble.predict_members(timed)
        probabilities = {
            **member_probabilities,
            ENSEMBLE_NAME: ensemble.combine(member_probabilities),
        }
        tree_counts = {member.name: member.tree_count for member in ensemble.members}
        calculator = MetricCalculator(timed)
        return [
            Evaluation(
                timing=timing,
                model=name,
                tree_count=tree_counts.get(name),
                rows=len(timed),
                log_loss=calculator.log_loss(probability),
                auc=calculator.auc(probability),
                brier=calculator.brier(probability),
                top_pick_place_rate=calculator.top_pick_place_rate(probability),
            )
            for name, probability in probabilities.items()
        ]
