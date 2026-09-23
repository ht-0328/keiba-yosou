"""多クラス分類の、モデルごとと、アンサンブルの当たり具合を測る。"""

from __future__ import annotations

from ..dataset import TrainingData
from ..feature import PredictionTiming
from ..ml_model import EnsembleModel
from .class_evaluation import ClassEvaluation
from .class_metric_calculator import ClassMetricCalculator
from .model_evaluator import ENSEMBLE_NAME


class ClassModelEvaluator:
    """1つの時点の多クラス分類のモデル（LightGBM・CatBoost）と、その平均の当たり具合を測る。``ModelEvaluator`` の多クラス版。"""

    def evaluate(self, timing: PredictionTiming, ensemble: EnsembleModel,
                 data: TrainingData) -> list[ClassEvaluation]:
        """``data`` は学習に使っていないデータ。モデルごとの行と、アンサンブルの行を返す。"""
        timed = data.for_timing(timing)
        member_probabilities = ensemble.predict_members(timed)
        probabilities = {
            **member_probabilities,
            ENSEMBLE_NAME: ensemble.combine(member_probabilities),
        }
        tree_counts = {member.name: member.tree_count for member in ensemble.members}
        calculator = ClassMetricCalculator(timed)
        upper_classes = list(timed.class_labels)[1:]
        return [
            ClassEvaluation(
                timing=timing,
                model=name,
                tree_count=tree_counts.get(name),
                rows=len(timed),
                accuracy=calculator.accuracy(probability),
                macro_f1=calculator.macro_f1(probability),
                mean_class_gap=calculator.mean_class_gap(probability),
                log_loss=calculator.log_loss(probability),
                cumulative_auc=tuple(calculator.cumulative_auc(probability, label) for label in upper_classes),
                confusion_matrix=calculator.confusion_matrix(probability),
            )
            for name, probability in probabilities.items()
        ]
