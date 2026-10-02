"""1つの単位の、3つのグループの近さのモデル。"""

from __future__ import annotations

import pandas as pd

from ..dataset import GROUPS
from .feature_matrix import FeatureMatrix
from .group_similarity import GroupSimilarity
from .score_columns import SCORE_COLUMNS


class UnitSimilarity:
    """1つの単位（芝ダート × 距離）の、勝利・馬券内・馬券外の3つのモデルと、共通の行列の変換。

    3つのモデルは同じ物差し（``FeatureMatrix``。単位の3つのグループを合わせた学習データで決める）で距離を測る。
    どのモデルも、そのグループの馬だけで作る。
    """

    def __init__(self, matrix: FeatureMatrix, k: int) -> None:
        self._matrix = matrix
        self._models = {group: GroupSimilarity(k) for group in GROUPS}
        self._rows: dict[str, int] = {}

    def fit(self, features: pd.DataFrame, targets: pd.DataFrame) -> UnitSimilarity:
        """``targets`` は勝利・馬券内・馬券外の列（1 ならそのグループ）。行の並びは ``features`` と同じ。"""
        matrix = self._matrix.fit(features).transform(features)
        self._rows = {group: int(targets[group].sum()) for group in self._models}
        for group, model in self._models.items():
            model.fit(matrix, targets[group].to_numpy() == 1)
        return self

    def scores(self, features: pd.DataFrame) -> pd.DataFrame:
        """行ごとの、3つのグループへの近さの点数。列は ``SCORE_COLUMNS`` の順。"""
        matrix = self._matrix.transform(features)
        return pd.DataFrame({SCORE_COLUMNS[group]: model.scores(matrix) for group, model in self._models.items()},
                            index=features.index)

    def group_rows(self) -> dict[str, int]:
        """グループの名前 → 覚えた頭数。"""
        return dict(self._rows)
