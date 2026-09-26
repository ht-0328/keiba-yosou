"""学習データ・予測用データの特徴量を、予想ごとの一覧に合わせ、前の組の予測の列を足す。"""

from __future__ import annotations

from dataclasses import replace
from typing import TypeVar

import pandas as pd

from yosou.shared.dataset import PredictionData, TrainingData
from yosou.shared.feature import FeatureCatalog, typed_features

#: 学習データか予測用データ（どちらも ``features``・``catalog`` を持つ）。
Data = TypeVar("Data", TrainingData, PredictionData)


class StackedColumns:
    """特徴量の表を、予想ごとの一覧（``catalog``）の列にし、前の組の予測（S・T）の列を足す（設計書 04 の 1・08 の 4）。

    学習データは元DB から1頭ごとと1レースごとの2回だけ作り、予想ごとの学習データは、ここで列を選び直して作る。
    前の組の予測が無い行（前の組が予測を出していない年）は、後の組の学習データから外す（設計書 16 の 7）。
    予測用データは行を外さない（前の組の予測は、必ず付いているため）。
    """

    def apply(self, data: Data, catalog: FeatureCatalog, stacked: pd.DataFrame | None = None) -> Data:
        """``stacked`` は ``data`` と同じ index の、前の組の予測から作った特徴量（無ければ None）。"""
        extra = stacked if stacked is not None else pd.DataFrame(index=data.features.index)
        combined = pd.concat([data.features, extra], axis=1)
        columns = list(self._columns_of(data, catalog))
        features = typed_features(combined[columns], catalog.categorical)
        placed = replace(data, features=features, catalog=catalog)
        if not isinstance(placed, TrainingData) or extra.empty:
            return placed
        return placed.where(extra.notna().all(axis=1))

    def _columns_of(self, data: Data, catalog: FeatureCatalog) -> tuple[str, ...]:
        """予測用データは、その時点で使う列だけ。学習データは一覧の全部（時点ごとの列は、学習のときに選ぶ）。"""
        if isinstance(data, PredictionData):
            return catalog.columns_for(data.timing)
        return catalog.names
