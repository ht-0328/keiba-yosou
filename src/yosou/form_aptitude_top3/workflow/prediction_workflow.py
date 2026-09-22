"""予測の流れを進める。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import DatasetBuilder
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import EnsembleModel
from yosou.shared.repository import ModelRepository

#: 予測の結果の、アンサンブルの確率の列の名前。
PROBABILITY = "3着以内に入る確率"


class PredictionWorkflow:
    """予測の流れ（設計書 05 の図2）。

    予測用データを作る → その時点のモデルを読み込む → 2つのモデルの予測確率を出して平均する。
    """

    def __init__(self, dataset_builder: DatasetBuilder, model_repository: ModelRepository) -> None:
        self._dataset_builder = dataset_builder
        self._model_repository = model_repository

    def run(self, race_id: str, timing: PredictionTiming) -> pd.DataFrame:
        """1レースの出走馬ごとの「3着以内に入る確率」。

        列は ID 列（レースID・開催日・馬ID・馬番・馬名）、``PROBABILITY``（平均）、モデルごとの確率。
        木曜は馬番が決まっていないので、馬番は空になる（馬ID・馬名で見分ける）。
        """
        data = self._dataset_builder.build_prediction_data(race_id, timing)
        ensemble = EnsembleModel(self._model_repository.load(timing))
        member_probabilities = ensemble.predict_members(data)
        average = ensemble.combine(member_probabilities)
        return data.ids.assign(**{PROBABILITY: average}, **member_probabilities)
