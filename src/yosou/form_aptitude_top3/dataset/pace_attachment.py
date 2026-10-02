"""学習データ・予測用データに、展開の予想の結果（まとまり P）の 20列を足す。"""

from __future__ import annotations

from dataclasses import replace
from typing import TypeVar

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID, PredictionData, TrainingData
from yosou.shared.feature import PACE_FORECAST_FEATURES, FeatureCatalog
from yosou.shared.feature.pace_forecast import PaceForecastTableBuilder

#: 学習データか予測用データ（どちらも ``ids``・``features``・``catalog`` を持つ）。
Data = TypeVar("Data", TrainingData, PredictionData)


class PaceAttachment:
    """``data`` の行に、同じ出走（レースID・馬ID）の P の 20列を足し、特徴量の一覧にも P を足す（設計書 09 の P）。

    P の元の予測（``forecasts``。1行 = 1頭、列 ``race_id``・``horse_id`` と ``pace_forecast.SOURCE_COLUMNS``）は呼ぶ側が渡す。
    学習データには、展開の予想の年ごとの確かめの予測（そのレースより前だけで学習した展開のモデルの予測。``PaceForecastHistory``）、
    予測用データには、保存した展開のモデルでそのレースを予測したもの（``DevelopmentPaceWorkflow``）。どちらも、その時点の展開の
    モデルの予測を渡す（木曜のモデルには木曜の予測）。予測の無い出走は欠損値。
    材料の組を1回作れば、時点ごとに P だけを付け替えられる（学習データを時点ごとに作り直さなくてよい）。
    """

    def apply(self, data: Data, forecasts: pd.DataFrame) -> Data:
        pace = PaceForecastTableBuilder().build(data.ids[RACE_ID], data.ids[HORSE_ID], forecasts)
        features = pd.concat([data.features.drop(columns=list(pace.columns), errors="ignore"),
                              pace.set_axis(data.features.index)], axis=1)
        return replace(data, features=features, catalog=self._catalog(data.catalog))

    def _catalog(self, catalog: FeatureCatalog) -> FeatureCatalog:
        """P を足した一覧（もう P があれば、そのまま）。"""
        names = set(catalog.names)
        return FeatureCatalog(catalog.features + tuple(feature for feature in PACE_FORECAST_FEATURES if feature.name not in names))
