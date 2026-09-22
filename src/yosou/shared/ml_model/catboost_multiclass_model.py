"""CatBoost で多クラス分類の学習・予測をする。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..dataset import TrainingData
from .catboost_model import CatBoostModel


class CatBoostMulticlassModel(CatBoostModel):
    """CatBoost で、クラスごとの確率を出す（荒れ具合の設計書 13）。``ClassProbabilityModel`` を守る。

    ``CatBoostModel`` との違いは3つ。目的関数が ``MultiClass``、目的変数を整数のクラス番号で渡す（学習データに
    全部のクラスがそろっていることを先に確かめる）、``predict_proba`` の全部の列（行数 × クラスの数）をそのまま返す。
    """

    loss_function = "MultiClass"

    def predict_proba(self, data) -> np.ndarray:
        """1行ずつの、クラスごとの確率（行数 × クラスの数。列の順はクラスの番号の順）。"""
        return super().predict_proba(data)

    def _check_labels(self, train: TrainingData) -> None:
        """CatBoost は目的変数に出てきた値をクラスとして扱うので、学習データに無いクラスがあれば止める。"""
        missing = sorted(set(train.class_labels) - set(self._label(train).unique()))
        if missing:
            raise ValueError(
                f"学習データに出てこないクラスがあります: {missing}（目的変数 {train.label_name}）。"
                "学習データの期間を延ばすか、線引きを見直してください。"
            )

    def _label(self, data: TrainingData) -> pd.Series:
        """クラス番号は整数で渡す。"""
        return data.label.astype(int)

    def _probabilities(self, matrix: np.ndarray) -> np.ndarray:
        return matrix
