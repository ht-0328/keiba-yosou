"""レースの荒れ具合の予想の予測を、期間の全レース × 券種に付ける。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from yosou.shared.dataset import TrainingData
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import EnsembleModel
from yosou.shared.repository import ModelRepository
from yosou.upset_level.dataset import BetType

from .upset_probability_table import UpsetProbabilityTable

#: 答え合わせ用の列。その券種の実際の荒れ具合（クラスの番号 0〜3。発売の無い券種は欠損）。
ACTUAL_LEVEL = "実際の荒れ具合（クラス番号）"


class RaceBatchPredictor:
    """荒れ具合の予想（1行 = 1レース）の、ある時点の券種ごとのモデルの予測を、期間の学習データの全レースに付ける。

    出る表は 1行 = 1レース × 券種。列は、ID 列・評価用の列・``PREDICTION_COLUMNS``（1レースの ``PredictionWorkflow`` と同じ）・
    ``ACTUAL_LEVEL``。
    """

    def __init__(self, repositories: Mapping[BetType, ModelRepository],
                 timing: PredictionTiming = PredictionTiming.RACE_DAY) -> None:
        self._repositories = dict(repositories)
        self._timing = timing

    def predict(self, data: TrainingData) -> pd.DataFrame:
        if len(data) == 0:
            raise LookupError("予測する行がありません（期間にレースがありません）")
        timed = data.for_timing(self._timing)
        return pd.concat([self._block(bet, timed) for bet in self._repositories], ignore_index=True)

    def _block(self, bet: BetType, timed: TrainingData) -> pd.DataFrame:
        """1つの券種の、全レースの予測。"""
        ensemble = EnsembleModel(self._repositories[bet].load(self._timing))
        probabilities = UpsetProbabilityTable(bet).build(ensemble.predict_proba(timed))
        actual = timed.targets[bet.column_name].reset_index(drop=True).rename(ACTUAL_LEVEL)
        base = pd.concat([timed.ids, timed.evaluation], axis=1).reset_index(drop=True)
        return pd.concat([base, probabilities, actual], axis=1)
