"""当たり具合を測るクラスの決まり（インターフェース）。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from ..dataset import TrainingData
from ..evaluation import ClassEvaluation, Evaluation
from ..feature import PredictionTiming
from ..ml_model import EnsembleModel


class Evaluator(Protocol):
    """当たり具合を測るクラスの決まり（``ModelEvaluator`` か ``ClassModelEvaluator``）。``TrainingWorkflow`` が受け取る。"""

    def evaluate(self, timing: PredictionTiming, ensemble: EnsembleModel,
                 data: TrainingData) -> Sequence[Evaluation | ClassEvaluation]:
        ...
