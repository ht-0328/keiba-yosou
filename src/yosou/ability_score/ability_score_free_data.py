"""学習データ・予測用データから、能力スコア（まとまり T）を外す。"""

from __future__ import annotations

from dataclasses import replace

from yosou.shared.dataset import PredictionData, TrainingData
from yosou.shared.feature import FeatureCatalog

from .features import ABILITY_SCORE_NAMES


class AbilityScoreFreeData:
    """T の4列を外し、特徴量の一覧からも T を除いたデータを返す。

    T を採用した時点では、学習データは T を含めて作り、採用しなかったモデル（3着以内か1着のどちらか）に渡す前にこのクラスで外す
    （S の ``DevelopmentScoreFreeData`` と同じ形）。T の無いデータに使っても、何も変わらない。
    """

    def training(self, data: TrainingData) -> TrainingData:
        return replace(data, features=self._without(data.features), catalog=self._catalog(data.catalog))

    def prediction(self, data: PredictionData) -> PredictionData:
        return replace(data, features=self._without(data.features), catalog=self._catalog(data.catalog))

    def _without(self, features):
        return features.drop(columns=list(ABILITY_SCORE_NAMES), errors="ignore")

    def _catalog(self, catalog: FeatureCatalog) -> FeatureCatalog:
        return FeatureCatalog(tuple(feature for feature in catalog.features if feature.name not in ABILITY_SCORE_NAMES))
