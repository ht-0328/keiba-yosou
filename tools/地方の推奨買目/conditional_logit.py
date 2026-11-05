"""条件つきロジット: グループ（レースなど）の中で1つだけ選ばれた行を、グループ内の softmax で当てはめる（外部ライブラリは使わない）。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ConditionalLogit:
    """``fit(X, groups, y)`` はニュートン法で係数を求め、``probabilities(u, groups)`` はグループごとの softmax を返す。

    ``X`` は行 × 特徴量、``groups`` は行ごとのグループの鍵（並び順は問わない）、``y`` は選ばれた行が 1（グループに1つ）。
    対数尤度 Σ (y·u − log Σ_group exp(u))（u = X·β）を最大にする。ヘッセ行列は Σ_group [Σ p x xᵀ − (Σ p x)(Σ p x)ᵀ]。
    """

    iterations: int = 40
    ridge: float = 1e-6
    tolerance: float = 1e-8

    def fit(self, X: np.ndarray, groups: np.ndarray, y: np.ndarray) -> np.ndarray:
        beta = np.zeros(X.shape[1])
        _, index = np.unique(groups, return_inverse=True)
        n_groups = int(index.max()) + 1
        for _ in range(self.iterations):
            p = self._softmax(X @ beta, index, n_groups)
            gradient = X.T @ (y - p)
            weighted = X * p[:, None]
            term1 = weighted.T @ X
            means = np.zeros((n_groups, X.shape[1]))
            np.add.at(means, index, weighted)
            hessian = term1 - means.T @ means + self.ridge * np.eye(X.shape[1])
            step = np.linalg.solve(hessian, gradient)
            beta = beta + step
            if np.abs(step).max() < self.tolerance:
                break
        return beta

    def probabilities(self, u: np.ndarray, groups: np.ndarray) -> np.ndarray:
        """``u``（X·β）をグループごとの softmax にする。"""
        _, index = np.unique(groups, return_inverse=True)
        return self._softmax(u, index, int(index.max()) + 1)

    def _softmax(self, u: np.ndarray, index: np.ndarray, n_groups: int) -> np.ndarray:
        u_max = np.full(n_groups, -np.inf)
        np.maximum.at(u_max, index, u)
        e = np.exp(u - u_max[index])
        z = np.zeros(n_groups)
        np.add.at(z, index, e)
        return e / z[index]
