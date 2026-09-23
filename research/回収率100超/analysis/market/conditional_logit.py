"""レース単位の条件付きロジットを学習する。"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

from .race_softmax import RaceSoftmax


class ConditionalLogit:
    """「このレースの中で、どの馬が勝つか」を学ぶ。

    1頭ずつ独立に学ぶ二値分類と違い、同じレースの馬を比べて学ぶ。勝った馬に付けた確率の log を
    最大にするように係数を決める。出てくる確率は、レースの中で必ず合計1になる。

    ``ridge`` は係数を 0 に引き寄せる強さ。節の多い折れ線が、学習データのわずかな凹凸に
    引きずられるのを抑える。
    """

    def __init__(self, ridge: float = 1e-4, max_iterations: int = 300) -> None:
        self._ridge = ridge
        self._max_iterations = max_iterations
        self._coefficients: np.ndarray | None = None

    @property
    def coefficients(self) -> np.ndarray:
        if self._coefficients is None:
            raise RuntimeError("まだ学習していません（fit を先に呼んでください）")
        return self._coefficients

    def fit(self, features: np.ndarray, race_index: np.ndarray, won: np.ndarray) -> ConditionalLogit:
        """``won`` は 1着なら 1、そうでなければ 0。"""
        softmax = RaceSoftmax(race_index)
        races = softmax.race_count

        def objective(beta: np.ndarray) -> tuple[float, np.ndarray]:
            probability = softmax.to_probability(features @ beta)
            loss = -np.log(np.clip(probability[won == 1], 1e-12, None)).sum() / races
            gradient = -(features.T @ (won - probability)) / races
            return loss + self._ridge * beta @ beta, gradient + 2 * self._ridge * beta

        start = np.zeros(features.shape[1])
        start[0] = 1.0
        result = minimize(objective, start, jac=True, method="L-BFGS-B",
                          options={"maxiter": self._max_iterations})
        self._coefficients = result.x
        return self

    def predict(self, features: np.ndarray, race_index: np.ndarray) -> np.ndarray:
        """レースの中で合計1になる勝率。"""
        return RaceSoftmax(race_index).to_probability(features @ self.coefficients)
