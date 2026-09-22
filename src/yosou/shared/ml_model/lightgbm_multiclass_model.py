"""LightGBM で多クラス分類の学習・予測をする。"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..dataset import TrainingData
from .lightgbm_model import LightGbmModel


class LightGbmMulticlassModel(LightGbmModel):
    """LightGBM で、クラスごとの確率を出す（荒れ具合の設計書 12）。``ClassProbabilityModel`` を守る。

    ``LightGbmModel`` との違いは3つ。目的関数が ``multiclass`` でクラスの数（``num_class``）を渡す、
    目的変数を整数のクラス番号で渡す、``predict_proba`` の全部の列（行数 × クラスの数）をそのまま返す。
    """

    objective = "multiclass"

    def predict_proba(self, data) -> np.ndarray:
        """1行ずつの、クラスごとの確率（行数 × クラスの数。列の順はクラスの番号の順）。"""
        return super().predict_proba(data)

    def _objective_params(self, train: TrainingData) -> dict[str, Any]:
        """クラスの数。学習データのクラスの並び（0〜3 など）から決め、設定ファイルには書かない（荒れ具合の設計書 14）。"""
        return {"num_class": len(train.class_labels)}

    def _label(self, data: TrainingData) -> pd.Series:
        """クラス番号は整数で渡す。"""
        return data.label.astype(int)

    def _probabilities(self, matrix: np.ndarray) -> np.ndarray:
        return matrix
