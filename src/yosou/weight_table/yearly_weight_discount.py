"""学習データに、レースの年ごとに「その年より前のレースだけで作った表 W」で体重の割引を付ける。"""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import pandas as pd

from yosou.shared.dataset import RACE_DATE, TrainingData
from yosou.shared.feature import FeatureCatalog

from .features import WEIGHT_DISCOUNT_FEATURES, WEIGHT_DISCOUNT_NAMES
from .weight_discount_columns import WeightDiscountColumns
from .weight_table_builder import WeightTableBuilder


class YearlyWeightDiscount:
    """学習データの行を開催日の年で分け、年ごとに「その年の1月1日より前のレースだけで作った表 W」（``prepared`` は ``WeightRuns`` の表）で
    V を付け、特徴量の一覧にも V を足す（リークを防ぐ。S の ``YearlyScorer`` と同じ決まり）。
    例: 2024年のレースの馬は、2023年までのレースで作った表で引く。もう V があれば置き換える。"""

    def __init__(self) -> None:
        self._builder = WeightTableBuilder()

    def apply(self, data: TrainingData, prepared: pd.DataFrame) -> TrainingData:
        years = pd.to_datetime(data.ids[RACE_DATE]).dt.year.to_numpy()
        parts = [WeightDiscountColumns(self._builder.build(prepared, before=date(int(year), 1, 1))).of(rows)
                 for year, rows in data.features.groupby(years, sort=True)]
        added = (pd.concat(parts).reindex(data.features.index) if parts
                 else pd.DataFrame(columns=list(WEIGHT_DISCOUNT_NAMES), index=data.features.index)).astype("float64")
        features = pd.concat([data.features.drop(columns=list(WEIGHT_DISCOUNT_NAMES), errors="ignore"), added], axis=1)
        return replace(data, features=features, catalog=self._catalog(data.catalog))

    def _catalog(self, catalog: FeatureCatalog) -> FeatureCatalog:
        names = set(catalog.names)
        return FeatureCatalog(catalog.features + tuple(feature for feature in WEIGHT_DISCOUNT_FEATURES if feature.name not in names))
