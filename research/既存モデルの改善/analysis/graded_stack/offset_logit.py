"""出発点（1段目のロジット）からのずらしだけを学ぶロジスティック回帰（3着以内の2段目）。"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize


class OffsetLogit:
    """確率 = sigmoid(出発点 + 切片 + 材料 · 係数)。係数には L2 の罰（``penalty`` × 係数の2乗の和 ÷ 2）を付け、
    材料が効かなければ出発点のまま（係数 0）に寄る。切片には罰を付けない（重賞の行で1段目が全体に高すぎる・低すぎるのを直す）。
    """

    def __init__(self, penalty: float) -> None:
        self._penalty = penalty
        self._weights: np.ndarray | None = None

    def fit(self, features: np.ndarray, offset: np.ndarray, label: np.ndarray) -> OffsetLogit:
        start = np.zeros(features.shape[1] + 1)
        result = minimize(self._loss, start, args=(features, offset, label.astype(float)), jac=True, method="L-BFGS-B")
        self._weights = result.x
        return self

    def predict(self, features: np.ndarray, offset: np.ndarray) -> np.ndarray:
        if self._weights is None:
            raise RuntimeError("fit を先に呼んでください")
        return 1.0 / (1.0 + np.exp(-(offset + self._weights[0] + features @ self._weights[1:])))

    def _loss(self, weights: np.ndarray, features: np.ndarray, offset: np.ndarray, label: np.ndarray) -> tuple[float, np.ndarray]:
        score = offset + weights[0] + features @ weights[1:]
        probability = 1.0 / (1.0 + np.exp(-score))
        loss = np.sum(np.logaddexp(0.0, score) - label * score) + 0.5 * self._penalty * np.sum(weights[1:] ** 2)
        residual = probability - label
        gradient = np.concatenate([[residual.sum()], features.T @ residual + self._penalty * weights[1:]])
        return float(loss), gradient
