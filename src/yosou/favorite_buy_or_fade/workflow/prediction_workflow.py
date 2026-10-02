"""予測の流れを進める。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import DatasetBuilder, OddsInput, OddsResolver, PopularityApplier, PopularityInput

from ..similarity import SimilarityModelSet
from .favorite_judgement import FavoriteJudgement


class PredictionWorkflow:
    """予測の流れ（設計書 05 の図2）。

    オッズを決める → 人気を決める（渡されなければオッズの小さい順）→ 学習した方針の時点で予測用データを作る
    （1番人気の行だけ）→ 3つのグループへの近さの点数と判定を出す。
    """

    def __init__(self, dataset_builder: DatasetBuilder, models: SimilarityModelSet,
                 popularity_applier: PopularityApplier, odds_resolver: OddsResolver) -> None:
        self._dataset_builder = dataset_builder
        self._judgement = FavoriteJudgement(models)
        self._timing = models.settings.timing
        self._popularity_applier = popularity_applier
        self._odds_resolver = odds_resolver

    def run(self, race_id: str, given: PopularityInput | None = None,
            given_odds: OddsInput | None = None) -> pd.DataFrame:
        """1レースの1番人気の、単位・3つの近さ・判定。1番人気がいなければ ``LookupError``。"""
        odds = self._odds_resolver.resolve(race_id, given_odds)
        popularity = self._popularity_applier.resolve(race_id, given, odds)
        data = self._dataset_builder.build_prediction_data(race_id, self._timing, popularity, odds)
        if len(data) == 0:
            raise LookupError(f"1番人気が分かりません。--pops 馬番:人気 か --odds で渡してください: {race_id}")
        return pd.concat([data.ids, self._judgement.judge(data.features)], axis=1)
