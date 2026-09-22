"""クラスごとの確率と正解から、多クラス分類の評価指標を計算する。"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, log_loss, roc_auc_score

from ..dataset import TrainingData


class ClassMetricCalculator:
    """1つのデータ（学習に使っていないもの）について、クラスごとの確率の当たり具合を計算する（荒れ具合の設計書 16 の 2）。

    「いちばん高いクラス」は、確率がいちばん大きい列のクラス番号。クラスの並びは学習データの ``class_labels``。
    """

    def __init__(self, data: TrainingData) -> None:
        self._label = data.label.to_numpy().astype(int)
        self._class_labels = list(data.class_labels)

    def accuracy(self, probabilities: np.ndarray) -> float:
        """正解率。いちばん高いクラスが、実際のクラスと一致した割合。"""
        return float(accuracy_score(self._label, self._top_class(probabilities)))

    def macro_f1(self, probabilities: np.ndarray) -> float:
        """マクロ F1。クラスごとの F1 を、クラスの数で平均する。少ないクラスも同じ重みで見る。"""
        top = self._top_class(probabilities)
        return float(f1_score(self._label, top, labels=self._class_labels, average="macro", zero_division=0))

    def confusion_matrix(self, probabilities: np.ndarray) -> tuple[tuple[int, ...], ...]:
        """混同行列。行が実際のクラス、列がいちばん高いクラス（どちらもクラスの番号の順）。"""
        matrix = confusion_matrix(self._label, self._top_class(probabilities), labels=self._class_labels)
        return tuple(tuple(int(count) for count in row) for row in matrix)

    def mean_class_gap(self, probabilities: np.ndarray) -> float:
        """クラスのずれの平均。いちばん高いクラスの番号と実際のクラスの番号の差の絶対値の平均（順序を活かせているか）。"""
        return float(np.abs(self._top_class(probabilities) - self._label).mean())

    def log_loss(self, probabilities: np.ndarray) -> float:
        """多クラスのログ損失。クラスごとの確率が正解から外れるほど大きい。"""
        return float(log_loss(self._label, probabilities, labels=self._class_labels))

    def cumulative_auc(self, probabilities: np.ndarray, from_class: int) -> float:
        """累積確率の AUC。「``from_class`` 以上のクラスになる確率」を二値の予測とみなした AUC。正解が片方しか無ければ NaN。"""
        is_at_or_above = self._label >= from_class
        if is_at_or_above.all() or not is_at_or_above.any():
            return float("nan")
        position = self._class_labels.index(from_class)
        return float(roc_auc_score(is_at_or_above, probabilities[:, position:].sum(axis=1)))

    def _top_class(self, probabilities: np.ndarray) -> np.ndarray:
        """1行ずつの、いちばん高いクラスの番号。"""
        return np.asarray(self._class_labels)[probabilities.argmax(axis=1)]
