"""予測の流れを進める。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import DatasetBuilder, PopularityApplier, PopularityInput
from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.group import POPULARITY_RANK
from yosou.shared.ml_model import EnsembleModel
from yosou.shared.repository import ModelRepository

from ..dataset import LongshotZone, LongshotZoneFilter

#: 予測の結果の、アンサンブルの確率の列の名前。
PROBABILITY = "3着以内に入る確率"


class PredictionWorkflow:
    """予測の流れ（設計書 05 の図2）。

    人気を決める → 予測用データを作る → その時点のモデルを読み込む → 2つのモデルの予測確率を平均する
    → 区分（中穴・大穴）が指定されていれば、その行だけにする。
    """

    def __init__(self, dataset_builder: DatasetBuilder, model_repository: ModelRepository,
                 popularity_applier: PopularityApplier, zone_filter: LongshotZoneFilter) -> None:
        self._dataset_builder = dataset_builder
        self._model_repository = model_repository
        self._popularity_applier = popularity_applier
        self._zone_filter = zone_filter

    def run(self, race_id: str, timing: PredictionTiming, given: PopularityInput | None = None,
            zone: LongshotZone | None = None) -> pd.DataFrame:
        """1レースの穴馬ごとの「3着以内に入る確率」。

        列は ID 列（レースID・開催日・馬ID・馬番・馬名）、穴馬の区分、人気順位、``PROBABILITY``（平均）、モデルごとの確率。
        木曜は馬番が決まっていないので、馬番は空になる（馬ID・馬名で見分ける）。
        ``given`` は利用者が ``--pops`` で渡した全頭の人気（木曜は必ず渡す。前日・当日で省略すると、元DB から決める）。
        ``zone`` を渡すと、その区分の穴馬の行だけにする。
        """
        popularity = self._popularity_applier.resolve(race_id, given)
        data = self._dataset_builder.build_prediction_data(race_id, timing, popularity)
        ensemble = EnsembleModel(self._model_repository.load(timing))
        member_probabilities = ensemble.predict_members(data)
        average = ensemble.combine(member_probabilities)
        ranks = data.features[POPULARITY_RANK]
        prediction = data.ids.assign(**{POPULARITY_RANK: ranks, PROBABILITY: average}, **member_probabilities)
        return self._zone_filter.apply(prediction, zone)
