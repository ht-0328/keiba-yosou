"""学習データの表。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from ..feature import FeatureCatalog, PredictionTiming
from .column_names import RACE_DATE

#: 二値分類の目的変数の値（0 と 1）。多クラス分類の予想は、作るときにクラスの並びを渡す。
BINARY_LABELS: tuple[int, ...] = (0, 1)


@dataclass(frozen=True)
class TrainingData:
    """学習データ（1行 = 1サンプル。1頭ごとの予想では1頭、レース単位の予想では1レース）。列を種類ごとの表に分けて持つ。4つの表は同じ行の並び。

    - ``ids``: ID 列（レースID・開催日 と、1頭ごとなら馬ID・馬番・馬名、レース単位なら競馬場・レース番号）。
    - ``features``: 特徴量。モデルの ``fit`` の ``X`` になる。
    - ``targets``: 目的変数（予想ごと。手本の予想では 3着以内・1着、荒れ具合の予想では券種ごとの4列）。
    - ``evaluation``: 評価用の列（確定着順・確定オッズ・払戻など）。
    - ``catalog``: ``features`` の元になった特徴量の一覧。
    - ``label_name``: ``targets`` のうち、モデルに当てさせる列の名前。
    - ``class_labels``: 目的変数の値の並び。二値分類は ``(0, 1)``、荒れ具合の予想は ``(0, 1, 2, 3)``。
    """

    ids: pd.DataFrame
    features: pd.DataFrame
    targets: pd.DataFrame
    evaluation: pd.DataFrame
    catalog: FeatureCatalog
    label_name: str
    class_labels: tuple[int, ...] = BINARY_LABELS

    def __len__(self) -> int:
        return len(self.ids)

    @property
    def label(self) -> pd.Series:
        """モデルに当てさせる目的変数。モデルの ``fit`` の ``y`` になる。"""
        return self.targets[self.label_name]

    @property
    def categorical_columns(self) -> tuple[str, ...]:
        """特徴量のうち、カテゴリ特徴量の名前（列の並び順）。"""
        return self.catalog.categorical_columns_of(self.features)

    def for_timing(self, timing: PredictionTiming) -> TrainingData:
        """特徴量を、その時点で使う列だけにした学習データ（設計書 07）。"""
        columns = list(self.catalog.columns_for(timing))
        return self._with_rows(self.ids, self.features[columns], self.targets, self.evaluation)

    def between(self, begin: date | None, end: date | None) -> TrainingData:
        """開催日が ``begin`` 以上 ``end`` 未満の行。None の端は区切らない。"""
        first = pd.Timestamp(begin) if begin else pd.Timestamp.min
        last = pd.Timestamp(end) if end else pd.Timestamp.max
        days = self.ids[RACE_DATE]
        is_inside = (days >= first) & (days < last)
        return self._with_rows(
            self.ids[is_inside], self.features[is_inside],
            self.targets[is_inside], self.evaluation[is_inside],
        )

    def with_label(self, label_name: str) -> TrainingData:
        """モデルに当てさせる列を ``label_name`` に持ち替えた学習データ（荒れ具合の設計書 08 の 2）。

        その列が欠損値の行（発売の無い券種のレースなど）は、学習できないので除く。無い列なら ``ValueError``。
        """
        if label_name not in self.targets.columns:
            names = "・".join(self.targets.columns)
            raise ValueError(f"目的変数の列がありません: {label_name}（ある列: {names}）")
        is_labeled = self.targets[label_name].notna()
        return TrainingData(
            self.ids[is_labeled], self.features[is_labeled], self.targets[is_labeled],
            self.evaluation[is_labeled], self.catalog, label_name, self.class_labels,
        )

    def _with_rows(self, ids: pd.DataFrame, features: pd.DataFrame, targets: pd.DataFrame,
                   evaluation: pd.DataFrame) -> TrainingData:
        """同じ一覧・同じ目的変数の列のまま、4つの表を入れ替えた学習データ。"""
        return TrainingData(ids, features, targets, evaluation, self.catalog, self.label_name, self.class_labels)
