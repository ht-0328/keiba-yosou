"""学習データの表。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from ..feature import PredictionTiming, categorical_columns_of
from .column_names import RACE_DATE, TOP3


@dataclass(frozen=True)
class TrainingData:
    """学習データ（1行 = 1レースの1頭）。列を種類ごとの表に分けて持つ。4つの表は同じ行の並び。

    - ``ids``: ID 列（レースID・開催日・馬ID・馬番・馬名）。
    - ``features``: 特徴量。モデルの ``fit`` の ``X`` になる。
    - ``targets``: 目的変数（3着以内・1着）。
    - ``evaluation``: 評価用の列（確定着順・確定オッズ・払戻など）。
    """

    ids: pd.DataFrame
    features: pd.DataFrame
    targets: pd.DataFrame
    evaluation: pd.DataFrame

    def __len__(self) -> int:
        return len(self.ids)

    @property
    def label(self) -> pd.Series:
        """モデルに当てさせる目的変数（3着以内なら 1）。モデルの ``fit`` の ``y`` になる。"""
        return self.targets[TOP3]

    @property
    def categorical_columns(self) -> tuple[str, ...]:
        """特徴量のうち、カテゴリ特徴量の名前（列の並び順）。"""
        return categorical_columns_of(self.features)

    def for_timing(self, timing: PredictionTiming) -> TrainingData:
        """特徴量を、その時点で使う列だけにした学習データ（設計書 07）。"""
        columns = list(timing.feature_columns())
        return TrainingData(self.ids, self.features[columns], self.targets, self.evaluation)

    def between(self, begin: date | None, end: date | None) -> TrainingData:
        """開催日が ``begin`` 以上 ``end`` 未満の行。None の端は区切らない。"""
        first = pd.Timestamp(begin) if begin else pd.Timestamp.min
        last = pd.Timestamp(end) if end else pd.Timestamp.max
        days = self.ids[RACE_DATE]
        is_inside = (days >= first) & (days < last)
        return TrainingData(
            self.ids[is_inside], self.features[is_inside],
            self.targets[is_inside], self.evaluation[is_inside],
        )
