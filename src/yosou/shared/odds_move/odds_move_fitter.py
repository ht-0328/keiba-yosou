"""オッズの動きの直しの重みを学ぶ。"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

from .odds_move_weights import OddsMoveWeights

#: 材料の重みの2乗の和に掛ける罰（行数で割った損失に足す）。切片には掛けない。
PENALTY = 1e-3
EPS = 1e-6


class OddsMoveFitter:
    """今の予想の確率のロジットを出発点（ずらし）にしたロジスティック回帰で、切片と材料の重みを学ぶ（材料の重みに弱い罰）。"""

    def fit(self, features: np.ndarray, hits: np.ndarray, probability: np.ndarray) -> OddsMoveWeights:
        """``features`` は ``OddsMoveFeatures.matrix``、``hits`` は当たり（1/0）、``probability`` は今の予想の確率。"""
        offset = logit(probability)
        y = np.asarray(hits, dtype=float)

        def loss(w: np.ndarray) -> tuple[float, np.ndarray]:
            p = 1.0 / (1.0 + np.exp(-(offset + w[0] + features @ w[1:])))
            value = -np.mean(y * np.log(np.clip(p, EPS, 1)) + (1 - y) * np.log(np.clip(1 - p, EPS, 1))) + PENALTY * np.sum(w[1:] ** 2)
            gradient = np.concatenate([[np.mean(p - y)], features.T @ (p - y) / len(y) + 2 * PENALTY * w[1:]])
            return value, gradient

        return OddsMoveWeights.of(minimize(loss, np.zeros(features.shape[1] + 1), jac=True, method="L-BFGS-B").x)


def logit(probability: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(probability, dtype=float), EPS, 1 - EPS)
    return np.log(clipped / (1 - clipped))
