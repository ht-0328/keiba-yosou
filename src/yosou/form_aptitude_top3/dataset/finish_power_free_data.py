"""学習データ・予測用データから、勝ち切る材料（まとまり Q）を外す。"""

from __future__ import annotations

from dataclasses import replace

from yosou.shared.dataset import PredictionData, TrainingData
from yosou.shared.feature import FeatureCatalog

from ..feature import FINISH_POWER_NAMES


class FinishPowerFreeData:
    """Q の 10列を外し、特徴量の一覧からも Q を除いたデータを返す（当日のモデルなら 295個 → 285個）。

    Q（勝ち切る材料）は1着のモデルだけが使う（設計書 15 の 15）。当日の学習データ・予測用データは Q を含めて1回で作り
    （``race_day_dataset_builder``）、3着以内のモデルに渡す前にこのクラスで Q を外す。1着のモデルには外さずに渡す。
    Q の無いデータ（木曜・前日・前の形）に使っても、何も変わらない。
    """

    def training(self, data: TrainingData) -> TrainingData:
        return replace(data, features=self._without(data.features), catalog=self._catalog(data.catalog))

    def prediction(self, data: PredictionData) -> PredictionData:
        return replace(data, features=self._without(data.features), catalog=self._catalog(data.catalog))

    def _without(self, features):
        return features.drop(columns=list(FINISH_POWER_NAMES), errors="ignore")

    def _catalog(self, catalog: FeatureCatalog) -> FeatureCatalog:
        return FeatureCatalog(tuple(feature for feature in catalog.features if feature.name not in FINISH_POWER_NAMES))
