"""学習データの行ごとに、そのレースの券種のオッズが無いか（N を使わないモデルで予測する行か）を答える。"""

from __future__ import annotations

import pandas as pd

from ..feature.feature_catalog import POOL_SUPPORT_NAMES
from .column_names import RACE_ID
from .training_data import TrainingData


class PoolFreeRows:
    """学習データ（テスト期間の行など）の行ごとに、そのレースで N（券種ごとのオッズから見た支持）の6列のどれか1列が
    全頭で欠損値なら真を返す。``PoolAvailability`` の判定（1レースの予測用データ）を、レースの混ざった学習データの形で行うもの。

    テスト期間の確かめ（``BacktestWorkflow``）で、券種のオッズの無いレースを N を使わないモデルに振り分けるのに使う
    （地方の設計書 06 の図3）。N の列が無いデータでは、全部の行が偽。
    """

    def of(self, data: TrainingData) -> pd.Series:
        columns = [name for name in POOL_SUPPORT_NAMES if name in data.features.columns]
        if not columns:
            return pd.Series(False, index=data.ids.index)
        missing_by_race = data.features[columns].isna().groupby(data.ids[RACE_ID].to_numpy()).transform("all")
        return missing_by_race.any(axis=1)
