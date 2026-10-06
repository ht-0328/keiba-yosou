"""学習データ・予測用データから、券種ごとのオッズから見た支持（まとまり N）を外す。"""

from __future__ import annotations

from dataclasses import replace

from ..feature.feature_catalog import POOL_SUPPORT_NAMES, FeatureCatalog
from .prediction_data import PredictionData
from .training_data import TrainingData


class PoolFreeData:
    """N の6列を外し、特徴量の一覧からも N を除いたデータを返す。

    当日に券種のオッズが無いレースは、N を使わないモデル（``券種オッズなし`` のフォルダに置く）で予測する。
    そのモデルは、当日の学習データからこのクラスで N を外して学ぶので、学習データを2回作らなくてよい。
    """

    def training(self, data: TrainingData) -> TrainingData:
        return replace(data, features=self._without(data.features), catalog=self._catalog(data.catalog))

    def prediction(self, data: PredictionData) -> PredictionData:
        return replace(data, features=self._without(data.features), catalog=self._catalog(data.catalog))

    def _without(self, features):
        return features.drop(columns=list(POOL_SUPPORT_NAMES), errors="ignore")

    def _catalog(self, catalog: FeatureCatalog) -> FeatureCatalog:
        return FeatureCatalog(tuple(feature for feature in catalog.features if feature.name not in POOL_SUPPORT_NAMES))
