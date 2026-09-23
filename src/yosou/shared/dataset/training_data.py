"""学習データの表。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from ..feature import FeatureCatalog, PredictionTiming
from .baseline_logit import BaselineLogit
from .column_names import RACE_DATE

#: 二値分類の目的変数の値（0 と 1）。多クラス分類の予想は、作るときにクラスの並びを渡す。
BINARY_LABELS: tuple[int, ...] = (0, 1)


@dataclass(frozen=True)
class TrainingData:
    """学習データ（1行 = 1サンプル。1頭ごとの予想では1頭、レース単位の予想では1レース）。列を種類ごとの表に分けて持つ。4つの表は同じ行の並び。

    - ``ids``: ID 列（レースID・開催日 と、1頭ごとなら馬ID・馬番・馬名、レース単位なら競馬場・レース番号）。
    - ``features``: 特徴量。モデルの ``fit`` の ``X`` になる。
    - ``targets``: 目的変数（予想ごと。手本の予想では 3着以内・1着・複勝的中、荒れ具合の予想では券種ごとの4列）。
    - ``evaluation``: 評価用の列（確定着順・確定オッズ・払戻など）。
    - ``catalog``: ``features`` の元になった特徴量の一覧。
    - ``label_name``: ``targets`` のうち、モデルに当てさせる列の名前。
    - ``class_labels``: 目的変数の値の並び。二値分類は ``(0, 1)``、荒れ具合の予想は ``(0, 1, 2, 3)``。
    - ``baseline``: 目的変数の基準（ロジット。既存モデルの修正計画の 1・2）。基準なしで学ぶ予想は None。
    """

    ids: pd.DataFrame
    features: pd.DataFrame
    targets: pd.DataFrame
    evaluation: pd.DataFrame
    catalog: FeatureCatalog
    label_name: str
    class_labels: tuple[int, ...] = BINARY_LABELS
    baseline: BaselineLogit | None = None

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
        """特徴量を、その時点で使う列だけにした学習データ（設計書 07）。基準も、その時点で使えるものだけ残す。"""
        columns = list(self.catalog.columns_for(timing))
        baseline = self.baseline.for_timing(timing) if self.baseline is not None else None
        return TrainingData(
            self.ids, self.features[columns], self.targets, self.evaluation,
            self.catalog, self.label_name, self.class_labels, baseline,
        )

    def between(self, begin: date | None, end: date | None) -> TrainingData:
        """開催日が ``begin`` 以上 ``end`` 未満の行。None の端は区切らない。"""
        first = pd.Timestamp(begin) if begin else pd.Timestamp.min
        last = pd.Timestamp(end) if end else pd.Timestamp.max
        days = self.ids[RACE_DATE]
        return self.where((days >= first) & (days < last))

    def where(self, rows: pd.Series) -> TrainingData:
        """``rows``（行ごとの真偽）が真の行だけの学習データ。人気帯や穴馬の区分ごとに分けて学ぶときにも使う。"""
        return TrainingData(
            self.ids[rows], self.features[rows], self.targets[rows], self.evaluation[rows],
            self.catalog, self.label_name, self.class_labels, self._baseline_at(rows),
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
            self.evaluation[is_labeled], self.catalog, label_name, self.class_labels, self._baseline_at(is_labeled),
        )

    def _baseline_at(self, rows: pd.Series) -> BaselineLogit | None:
        """行を選んだ基準。基準が無ければ None。"""
        if self.baseline is None:
            return None
        return self.baseline.at(rows)
