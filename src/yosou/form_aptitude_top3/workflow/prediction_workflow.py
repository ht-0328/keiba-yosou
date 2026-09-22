"""予測の流れを進める。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import DatasetBuilder, PredictionData
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import EnsembleModel
from yosou.shared.repository import ModelRepository

from ..dataset import OddsInput, OddsResolver
from ..feature import WIN_ODDS

#: 予測の結果の、アンサンブルの確率の列の名前。
PROBABILITY = "3着以内に入る確率"


class PredictionWorkflow:
    """予測の流れ（設計書 05 の図2）。

    オッズを決める → 予測用データを作る → その時点のモデルを読み込む → 2つのモデルの予測確率を出して平均する。
    """

    def __init__(self, dataset_builder: DatasetBuilder, model_repository: ModelRepository,
                 odds_resolver: OddsResolver) -> None:
        self._dataset_builder = dataset_builder
        self._model_repository = model_repository
        self._odds_resolver = odds_resolver

    def run(self, race_id: str, timing: PredictionTiming,
            given: OddsInput | None = None) -> pd.DataFrame:
        """1レースの出走馬ごとの「3着以内に入る確率」。

        列は ID 列（レースID・開催日・馬ID・馬番・馬名）、単勝オッズ（前日・当日だけ）、``PROBABILITY``（平均）、
        モデルごとの確率。木曜は馬番が決まっていないので、馬番は空になる（馬ID・馬名で見分ける）。
        ``given`` は利用者が ``--odds`` で渡したオッズ（省略すると、元DB から決める）。
        """
        odds = self._odds_resolver.resolve(race_id, given)
        data = self._dataset_builder.build_prediction_data(race_id, timing, odds=odds)
        ensemble = EnsembleModel(self._model_repository.load(timing))
        member_probabilities = ensemble.predict_members(data)
        average = ensemble.combine(member_probabilities)
        return data.ids.assign(**self._shown_odds(data), **{PROBABILITY: average}, **member_probabilities)

    def _shown_odds(self, data: PredictionData) -> dict[str, pd.Series]:
        """結果の表に出す単勝オッズ。木曜はオッズを使わないので、列を出さない（設計書 07）。"""
        if WIN_ODDS not in data.features.columns:
            return {}
        return {WIN_ODDS: data.features[WIN_ODDS]}
