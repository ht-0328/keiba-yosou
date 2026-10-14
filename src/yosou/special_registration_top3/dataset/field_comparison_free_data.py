"""学習データ・予測用データから、同じレースの相手と比べる材料（70個）を外す。"""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from yosou.shared.dataset import PredictionData, TrainingData
from yosou.shared.feature import FeatureCatalog

from ..feature import FIELD_COMPARISON_NAMES


class FieldComparisonFreeData:
    """相手と比べる材料の 70列（``FIELD_COMPARISON_NAMES``）を外し、特徴量の一覧からも除いたデータを返す。

    学習では出走馬の中で、予測では登録馬の中で比べる材料は、出走しない馬が混ざるぶんずれる。``backtest --variant 相手と比べない``
    で、この 70個を外した 110個の版も同じ区切りで学んで比べる（設計書 16 の 4）。無い列は無視する。
    """

    def training(self, data: TrainingData) -> TrainingData:
        return replace(data, features=self._without(data.features), catalog=self._catalog(data.catalog))

    def prediction(self, data: PredictionData) -> PredictionData:
        return replace(data, features=self._without(data.features), catalog=self._catalog(data.catalog))

    def _without(self, features: pd.DataFrame) -> pd.DataFrame:
        return features.drop(columns=list(FIELD_COMPARISON_NAMES), errors="ignore")

    def _catalog(self, catalog: FeatureCatalog) -> FeatureCatalog:
        return FeatureCatalog(tuple(feature for feature in catalog.features if feature.name not in FIELD_COMPARISON_NAMES))
