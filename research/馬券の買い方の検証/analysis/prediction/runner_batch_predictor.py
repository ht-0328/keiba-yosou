"""1頭ごとの予想の予測を、期間の全行に付ける。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import TrainingData
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import EnsembleModel
from yosou.shared.repository import ModelRepository


class RunnerBatchPredictor:
    """1頭ごとの予想（近走と適性・人気馬・穴馬）の、ある時点のモデルの予測を、期間の学習データの全行に付ける。

    予想モデルの ``ModelEvaluator`` が検証データに対してしていること（時点の列にそろえる → 2つのモデルで予測 → 平均）と同じ。
    出る表の列は、ID 列・評価用の列・``probability_column``（平均）・モデルごとの確率（LightGBM・CatBoost）。
    """

    def __init__(self, model_repository: ModelRepository, probability_column: str,
                 timing: PredictionTiming = PredictionTiming.RACE_DAY) -> None:
        self._model_repository = model_repository
        self._probability_column = probability_column
        self._timing = timing

    def predict(self, data: TrainingData) -> pd.DataFrame:
        if len(data) == 0:
            raise LookupError("予測する行がありません（期間に出走がありません）")
        timed = data.for_timing(self._timing)
        ensemble = EnsembleModel(self._model_repository.load(self._timing))
        members = ensemble.predict_members(timed)
        columns = pd.concat([timed.ids, timed.evaluation], axis=1).reset_index(drop=True)
        return columns.assign(**{self._probability_column: ensemble.combine(members)}, **members)
