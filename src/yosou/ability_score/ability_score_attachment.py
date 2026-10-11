"""学習データ・予測用データに、能力スコア（まとまり T）の4列を足す。"""

from __future__ import annotations

from dataclasses import replace
from typing import TypeVar

import pandas as pd

from yosou.shared.dataset import RACE_ID, PredictionData, TrainingData
from yosou.shared.feature import FeatureCatalog

from .ability_score_columns import AbilityScoreColumns
from .features import ABILITY_SCORE_FEATURES, ABILITY_SCORE_NAMES

#: 学習データか予測用データ（どちらも ``ids``・``features``・``catalog`` を持つ）。
Data = TypeVar("Data", TrainingData, PredictionData)


class AbilityScoreAttachment:
    """``data`` の特徴量にもうある能力指数と斤量（馬の力の材料 M）から、T の4列を作って足し、特徴量の一覧にも T を足す。

    S（展開スコア）の ``ScoreAttachment`` と同じ形だが、外の表は要らない（レースより前の走から作った能力指数と今回の斤量だけから
    出すので、学習データでも予測用データでも同じ計算でよく、リークは起きない）。もう T があれば置き換える。
    """

    def apply(self, data: Data) -> Data:
        added = AbilityScoreColumns().of(data.features, data.ids[RACE_ID])
        features = pd.concat([data.features.drop(columns=list(ABILITY_SCORE_NAMES), errors="ignore"), added], axis=1)
        return replace(data, features=features, catalog=self._catalog(data.catalog))

    def _catalog(self, catalog: FeatureCatalog) -> FeatureCatalog:
        """T を足した一覧（もう T があれば、そのまま）。"""
        names = set(catalog.names)
        return FeatureCatalog(catalog.features + tuple(feature for feature in ABILITY_SCORE_FEATURES if feature.name not in names))
