"""Stern の補正の強さ（λ・μ）を、実際の着順から決める。"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

#: log を取る値の下限。
_FLOOR = 1e-12


class SternExponentFitter:
    """実際の「1着 → 2着 → 3着」の並びが、いちばん起きやすくなる λ・μ を探す（最尤法）。

    λ・μ は 2着・3着を決めるときの重みのべき（``FinishOrderProbability``）。1 なら Harville の式そのもので、
    小さいほど2着・3着で人気馬の寄りが弱くなる。``races`` は ``RaceFinishes.build`` の並び。
    """

    def __init__(self, max_iterations: int = 200) -> None:
        self._max_iterations = max_iterations

    def fit(self, races: list[tuple[np.ndarray, int, int, int]]) -> tuple[float, float]:
        """（λ, μ）。レースが無ければ（1, 1）。"""
        if not races:
            return 1.0, 1.0
        result = minimize(self._negative_log_likelihood, np.array([0.9, 0.8]), args=(races,), method="Nelder-Mead",
                          options={"xatol": 1e-3, "fatol": 1e-5, "maxiter": self._max_iterations})
        return float(result.x[0]), float(result.x[1])

    def _negative_log_likelihood(self, exponents: np.ndarray, races: list[tuple[np.ndarray, int, int, int]]) -> float:
        lam, mu = exponents
        total = sum(self._race(probability, first, second, third, lam, mu)
                    for probability, first, second, third in races)
        return -total / len(races)

    def _race(self, p: np.ndarray, first: int, second: int, third: int, lam: float, mu: float) -> float:
        """1レースの、実際の並び（2着と3着の部分）の log 尤度。1着の部分は λ・μ によらないので足さない。"""
        second_weight = np.power(p, lam)
        third_weight = np.power(p, mu)
        second_share = second_weight[second] / max(second_weight.sum() - second_weight[first], _FLOOR)
        third_rest = third_weight.sum() - third_weight[first] - third_weight[second]
        third_share = third_weight[third] / max(third_rest, _FLOOR)
        return float(np.log(max(second_share, _FLOOR)) + np.log(max(third_share, _FLOOR)))
