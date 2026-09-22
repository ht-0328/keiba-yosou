"""予測用データの表。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..feature import PredictionTiming, categorical_columns_of


@dataclass(frozen=True)
class PredictionData:
    """予測用データ（1行 = 1頭）。1レースの出走馬について、``timing`` の時点で使う特徴量だけを持つ。

    学習データから、目的変数と評価用の列を除いた形（設計書 08 の 2）。
    """

    ids: pd.DataFrame
    features: pd.DataFrame
    timing: PredictionTiming

    def __len__(self) -> int:
        return len(self.ids)

    @property
    def categorical_columns(self) -> tuple[str, ...]:
        """特徴量のうち、カテゴリ特徴量の名前（列の並び順）。"""
        return categorical_columns_of(self.features)
