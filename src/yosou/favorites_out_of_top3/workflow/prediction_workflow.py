"""予測の流れを進める。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import DatasetBuilder
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import EnsembleModel
from yosou.shared.repository import ModelRepository

from ..dataset import PopularityApplier, PopularityInput
from ..feature import POPULARITY_RANK
from .prediction_timings import TIMING_CHOICES, TIMINGS

#: 予測の結果の、アンサンブルの確率の列の名前。
PROBABILITY = "4着以下になる確率"


class PredictionWorkflow:
    """予測の流れ（設計書 05 の図2）。

    人気を決める → 予測用データを作る → その時点のモデルを読み込む → 2つのモデルの予測確率を平均する。
    """

    def __init__(self, dataset_builder: DatasetBuilder, model_repository: ModelRepository,
                 popularity_applier: PopularityApplier) -> None:
        self._dataset_builder = dataset_builder
        self._model_repository = model_repository
        self._popularity_applier = popularity_applier

    def run(self, race_id: str, timing: PredictionTiming,
            given: PopularityInput | None = None) -> pd.DataFrame:
        """1レースの人気馬ごとの「4着以下になる確率」。

        列は ID 列（レースID・開催日・馬ID・馬番・馬名）、人気順位、``PROBABILITY``（平均）、モデルごとの確率。
        ``given`` は利用者が ``--pops`` で渡した人気（省略すると、元DB から決める）。
        """
        self._check_timing(timing)
        popularity = self._popularity_applier.resolve(race_id, given)
        data = self._dataset_builder.build_prediction_data(race_id, timing, popularity)
        ensemble = EnsembleModel(self._model_repository.load(timing))
        member_probabilities = ensemble.predict_members(data)
        average = ensemble.combine(member_probabilities)
        ranks = data.features[POPULARITY_RANK]
        return data.ids.assign(**{POPULARITY_RANK: ranks, PROBABILITY: average},
                               **member_probabilities)

    def _check_timing(self, timing: PredictionTiming) -> None:
        """この予想は、人気の見当が付く前日・当日だけ予測を出す（設計書 07）。"""
        if timing not in TIMINGS:
            raise ValueError(
                f"この予想は前日・当日だけです（{timing.label}では、馬番も人気も決まっていません）。"
                f"--timing は {TIMING_CHOICES} のどちらかです"
            )
