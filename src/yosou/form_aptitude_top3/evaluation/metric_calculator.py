"""予測確率と正解から、評価指標を計算する。"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from ..dataset import RACE_ID, TrainingData

#: 目的変数の値（0 と 1）。
_LABELS = [0, 1]


class MetricCalculator:
    """1つのデータ（学習に使っていないもの）について、予測確率の当たり具合を計算する。"""

    def __init__(self, data: TrainingData) -> None:
        self._label = data.label.to_numpy()
        self._race_ids = data.ids[RACE_ID].to_numpy()

    def log_loss(self, probability: np.ndarray) -> float:
        """ログ損失。確率が正解から外れるほど大きい。"""
        return float(log_loss(self._label, probability, labels=_LABELS))

    def auc(self, probability: np.ndarray) -> float:
        """AUC。3着以内の馬に、そうでない馬より高い確率を付けられた割合。正解が片方しか無ければ NaN。"""
        has_both_labels = len(np.unique(self._label)) == len(_LABELS)
        if not has_both_labels:
            return float("nan")
        return float(roc_auc_score(self._label, probability))

    def brier(self, probability: np.ndarray) -> float:
        """Brier スコア。確率と正解（0 か 1）の差の2乗の平均。"""
        return float(brier_score_loss(self._label, probability))

    def top_pick_place_rate(self, probability: np.ndarray) -> float:
        """各レースで確率がいちばん高い馬が、3着以内に入った割合。"""
        runners = pd.DataFrame({
            "race": self._race_ids, "probability": probability, "label": self._label,
        })
        top_pick_rows = runners.groupby("race", sort=False)["probability"].idxmax()
        return float(runners.loc[top_pick_rows, "label"].mean())
