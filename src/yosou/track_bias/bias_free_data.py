"""学習データ・予測用データから、トラックバイアスの補正（まとまり U）を外す。"""

from __future__ import annotations

from dataclasses import replace

from yosou.shared.dataset import PredictionData, TrainingData
from yosou.shared.feature import FeatureCatalog

from .features import TRACK_BIAS_NAMES


class TrackBiasFreeData:
    """U の5列を外し、特徴量の一覧からも U を除いたデータを返す。

    U を採用した時点では、学習データは U を含めて作り、採用しなかったモデル（3着以内か1着のどちらか）に渡す前にこのクラスで外す
    （S の ``DevelopmentScoreFreeData`` と同じ形）。U の無いデータに使っても、何も変わらない。
    """

    def training(self, data: TrainingData) -> TrainingData:
        return replace(data, features=self._without(data.features), catalog=self._catalog(data.catalog))

    def prediction(self, data: PredictionData) -> PredictionData:
        return replace(data, features=self._without(data.features), catalog=self._catalog(data.catalog))

    def _without(self, features):
        return features.drop(columns=list(TRACK_BIAS_NAMES), errors="ignore")

    def _catalog(self, catalog: FeatureCatalog) -> FeatureCatalog:
        return FeatureCatalog(tuple(feature for feature in catalog.features if feature.name not in TRACK_BIAS_NAMES))
