"""レースの中で比べて1着の確率を出す、出発点つきの条件付きロジット（1着の2段目）。"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize


class ConditionalLogit:
    """1着の確率 = exp(出発点 + 材料 · 係数) をレースの全頭で合計 1 にしたもの（条件付きロジット）。

    出発点は1段目の1着の確率の対数（レースの中で比べるので、どの馬にも同じ値を足しても変わらず、切片は要らない）。
    係数には L2 の罰を付け、材料が効かなければ1段目の確率（をレースで合計 1 にしたもの）のまま。
    ``groups`` は行ごとのレースの番号（0 から、同じレースの行は続けて並ぶ必要はない）。
    """

    def __init__(self, penalty: float) -> None:
        self._penalty = penalty
        self._weights: np.ndarray | None = None

    def fit(self, features: np.ndarray, offset: np.ndarray, label: np.ndarray, groups: np.ndarray) -> ConditionalLogit:
        start = np.zeros(features.shape[1])
        result = minimize(self._loss, start, args=(features, offset, label.astype(float), groups), jac=True, method="L-BFGS-B")
        self._weights = result.x
        return self

    def predict(self, features: np.ndarray, offset: np.ndarray, groups: np.ndarray) -> np.ndarray:
        if self._weights is None:
            raise RuntimeError("fit を先に呼んでください")
        return self._softmax(offset + features @ self._weights, groups)

    def _softmax(self, score: np.ndarray, groups: np.ndarray) -> np.ndarray:
        top = np.full(groups.max() + 1, -np.inf)
        np.maximum.at(top, groups, score)
        exp = np.exp(score - top[groups])
        total = np.zeros(groups.max() + 1)
        np.add.at(total, groups, exp)
        return exp / total[groups]

    def _loss(self, weights: np.ndarray, features: np.ndarray, offset: np.ndarray, label: np.ndarray,
              groups: np.ndarray) -> tuple[float, np.ndarray]:
        probability = self._softmax(offset + features @ weights, groups)
        loss = -np.sum(label * np.log(np.clip(probability, 1e-15, None))) + 0.5 * self._penalty * np.sum(weights ** 2)
        # 勝った馬の数がレースで1頭なら、勾配は Σ（確率 − 勝ち）× 材料
        winners = np.zeros(groups.max() + 1)
        np.add.at(winners, groups, label)
        gradient = features.T @ (probability * winners[groups] - label) + self._penalty * weights
        return float(loss), gradient
