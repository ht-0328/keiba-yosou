"""学習データ・予測用データから、馬体重の表の割引（まとまり V）を外す。"""

from __future__ import annotations

from dataclasses import replace

from yosou.shared.dataset import PredictionData, TrainingData
from yosou.shared.feature import FeatureCatalog

from .features import WEIGHT_DISCOUNT_NAMES


class WeightDiscountFreeData:
    """V の列を外し、特徴量の一覧からも V を除いたデータを返す（S の ``DevelopmentScoreFreeData`` と同じ形）。V の無いデータに使っても、何も変わらない。"""

    def training(self, data: TrainingData) -> TrainingData:
        return replace(data, features=self._without(data.features), catalog=self._catalog(data.catalog))

    def prediction(self, data: PredictionData) -> PredictionData:
        return replace(data, features=self._without(data.features), catalog=self._catalog(data.catalog))

    def _without(self, features):
        return features.drop(columns=list(WEIGHT_DISCOUNT_NAMES), errors="ignore")

    def _catalog(self, catalog: FeatureCatalog) -> FeatureCatalog:
        return FeatureCatalog(tuple(feature for feature in catalog.features if feature.name not in WEIGHT_DISCOUNT_NAMES))
