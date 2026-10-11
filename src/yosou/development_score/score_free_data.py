"""学習データ・予測用データから、展開スコア（まとまり S）を外す。"""

from __future__ import annotations

from dataclasses import replace

from yosou.shared.dataset import PredictionData, TrainingData
from yosou.shared.feature import FeatureCatalog

from .features import DEVELOPMENT_SCORE_NAMES


class DevelopmentScoreFreeData:
    """S の 5列を外し、特徴量の一覧からも S を除いたデータを返す。

    S（展開スコア）は前日の3着以内のモデルだけが使う（近走と適性の予想の設計書 15 の 17。1着のモデルは採用の基準を満たさなかった）。
    前日の学習データは S を含めて作り、1着のモデルに渡す前にこのクラスで S を外す（Q を3着以内のモデルから外す ``FinishPowerFreeData`` の逆）。
    S の無いデータに使っても、何も変わらない。
    """

    def training(self, data: TrainingData) -> TrainingData:
        return replace(data, features=self._without(data.features), catalog=self._catalog(data.catalog))

    def prediction(self, data: PredictionData) -> PredictionData:
        return replace(data, features=self._without(data.features), catalog=self._catalog(data.catalog))

    def _without(self, features):
        return features.drop(columns=list(DEVELOPMENT_SCORE_NAMES), errors="ignore")

    def _catalog(self, catalog: FeatureCatalog) -> FeatureCatalog:
        return FeatureCatalog(tuple(feature for feature in catalog.features if feature.name not in DEVELOPMENT_SCORE_NAMES))
