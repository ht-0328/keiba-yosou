"""学習データ・予測用データに、馬体重の表の割引（まとまり V）の列を足す。"""

from __future__ import annotations

from dataclasses import replace
from typing import TypeVar

import pandas as pd

from yosou.shared.dataset import PredictionData, TrainingData
from yosou.shared.feature import FeatureCatalog

from .features import WEIGHT_DISCOUNT_FEATURES, WEIGHT_DISCOUNT_NAMES
from .weight_discount_columns import WeightDiscountColumns
from .weight_table import WeightTable

#: 学習データか予測用データ（どちらも ``ids``・``features``・``catalog`` を持つ）。
Data = TypeVar("Data", TrainingData, PredictionData)


class WeightDiscountAttachment:
    """``data`` の特徴量にもうある増減・前走からの日数・馬齢から、表 W（``table``）を引いて V の列を足し、特徴量の一覧にも V を足す。

    T の ``AbilityScoreAttachment`` と同じく外の出走の表は要らないが、表 W は要る（予測では ``WeightTableStore`` の表、学習では
    ``YearlyWeightDiscount`` が年ごとの表で付ける）。もう V があれば置き換える。
    """

    def __init__(self, table: WeightTable) -> None:
        self._columns = WeightDiscountColumns(table)

    def apply(self, data: Data) -> Data:
        added = self._columns.of(data.features)
        features = pd.concat([data.features.drop(columns=list(WEIGHT_DISCOUNT_NAMES), errors="ignore"), added], axis=1)
        return replace(data, features=features, catalog=self._catalog(data.catalog))

    def _catalog(self, catalog: FeatureCatalog) -> FeatureCatalog:
        """V を足した一覧（もう V があれば、そのまま）。"""
        names = set(catalog.names)
        return FeatureCatalog(catalog.features + tuple(feature for feature in WEIGHT_DISCOUNT_FEATURES if feature.name not in names))
