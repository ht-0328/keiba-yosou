"""学習データ・予測用データから、券種ごとのオッズから見た支持（まとまり N）を外す。"""

from __future__ import annotations

from dataclasses import replace

from yosou.shared.dataset import PredictionData, TrainingData

from yosou.shared.feature import FeatureCatalog

from ..feature import POOL_SUPPORT_NAMES


class PoolFreeData:
    """N の6列を外し、特徴量の一覧からも N を除いたデータを返す（当日のモデルなら 285個 → 279個）。

    当日に券種のオッズが無いレースは、N を使わないモデル（``POOL_FREE_FOLDER`` に置く）で予測する。
    そのモデルは、当日の学習データ（``race_day_dataset_builder``）からこのクラスで N を外して学ぶので、
    学習データを2回作らなくてよい。
    """

    def training(self, data: TrainingData) -> TrainingData:
        return replace(data, features=self._without(data.features), catalog=self._catalog(data.catalog))

    def prediction(self, data: PredictionData) -> PredictionData:
        return replace(data, features=self._without(data.features), catalog=self._catalog(data.catalog))

    def _without(self, features):
        return features.drop(columns=list(POOL_SUPPORT_NAMES), errors="ignore")

    def _catalog(self, catalog: FeatureCatalog) -> FeatureCatalog:
        return FeatureCatalog(tuple(feature for feature in catalog.features if feature.name not in POOL_SUPPORT_NAMES))
