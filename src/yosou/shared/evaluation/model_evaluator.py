"""モデルごとと、アンサンブルの当たり具合を測る。"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

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
        return self.evaluate_probabilities(timing, timed, probabilities, tree_counts)

    def evaluate_probabilities(self, timing: PredictionTiming, data: TrainingData,
                               probabilities: Mapping[str, np.ndarray],
                               tree_counts: Mapping[str, int | None] | None = None) -> list[Evaluation]:
        """出し終えた確率（モデルの名前 → 行ごとの確率）の当たり具合を、名前ごとに1行ずつ測る。

        ``data`` は確率と同じ行の並びのデータ（その時点の列にしてあるもの）。モデルを持たずに確率だけがあるとき
        （テスト期間の確かめで、券種のオッズの有無でモデルを使い分けた確率や、市場の確率）に使う。
        ``tree_counts`` は名前 → 木の数（無ければ None）。
        """
        counts = dict(tree_counts or {})
        calculator = MetricCalculator(data)
        return [
            Evaluation(
                timing=timing,
                model=name,
                tree_count=counts.get(name),
                rows=len(data),
                log_loss=calculator.log_loss(probability),
                auc=calculator.auc(probability),
                brier=calculator.brier(probability),
                top_pick_place_rate=calculator.top_pick_place_rate(probability),
                top_pick_place_payback=calculator.top_pick_place_payback(probability),
                popularity_pick_place_rate=calculator.popularity_pick_place_rate(),
                popularity_pick_place_payback=calculator.popularity_pick_place_payback(),
                auc_within_popularity=calculator.auc_within_popularity(probability),
            )
            for name, probability in probabilities.items()
        ]
