"""Stern のべき乗（2着・3着の寄せ方）を、実際の着順から推定する。"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize


class SternFitter:
    """観測した「1着 → 2着 → 3着」の並びがいちばん起きやすくなる λ・μ を探す。

    Harville モデル（λ = μ = 1）は、1着が決まったあとの2着・3着も勝率の比で決まると考える。
    これは人気馬が上位を独占しすぎる形になり、実際より高く見積もる（3着以内の確率で最大 10 ポイントのずれ）。
    λ・μ を 1 より小さくすると、2着・3着では人気馬の寄りが弱まり、実際に近づく。

    ``races`` は、1レースぶんの（勝率, 1着の位置, 2着の位置, 3着の位置）の並び。
    """

    def __init__(self, max_iterations: int = 200) -> None:
        self._max_iterations = max_iterations

    def fit(self, races: list[tuple[np.ndarray, int, int, int]]) -> tuple[float, float]:
        """（λ, μ）を返す。"""
        result = minimize(self._negative_log_likelihood, np.array([1.0, 1.0]), args=(races,),
                          method="Nelder-Mead",
                          options={"xatol": 1e-3, "fatol": 1e-4, "maxiter": self._max_iterations})
        return float(result.x[0]), float(result.x[1])

    def _negative_log_likelihood(self, parameters: np.ndarray,
                                 races: list[tuple[np.ndarray, int, int, int]]) -> float:
        lam, mu = parameters
        total = 0.0
        for probability, first, second, third in races:
            total += self._race_log_likelihood(probability, first, second, third, lam, mu)
        return -total / len(races)

    def _race_log_likelihood(self, probability: np.ndarray, first: int, second: int, third: int,
                             lam: float, mu: float) -> float:
        """1レースぶんの、観測した並びの log 尤度。"""
        second_weight = np.power(probability, lam)
        third_weight = np.power(probability, mu)
        return (np.log(max(probability[first], 1e-12))
                + np.log(max(second_weight[second], 1e-12))
                - np.log(max(second_weight.sum() - second_weight[first], 1e-12))
                + np.log(max(third_weight[third], 1e-12))
                - np.log(max(third_weight.sum() - third_weight[first] - third_weight[second], 1e-12)))
