"""組の確率の重みを、罰則つきの条件付きロジットで推定する。"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize


class PenalizedBlendFitter:
    """本番の ``ComboBlendFitter`` と同じ条件付きロジットの最尤推定に、``penalized`` の列の重みへの L2 の罰則（``penalty`` × 重みの2乗の和）を足す。

    行はレースごとにまとまっていること（``starts`` は各レースの最初の行の位置）。当たった組の無いレースは呼ぶ側で落とす。
    出発点は「その券種自身の市場だけ」（最初の列 1・ほか 0）。罰則 0 で差の列が無ければ、本番の ``ComboBlendFitter`` と同じ重みになる。
    """

    def __init__(self, penalty: float = 0.0) -> None:
        self._penalty = penalty

    def fit(self, features: np.ndarray, hit: np.ndarray, starts: np.ndarray, penalized: np.ndarray) -> np.ndarray:
        start = np.zeros(features.shape[1])
        start[0] = 1.0
        mask = penalized.astype(float)
        result = minimize(self._loss, start, args=(features, hit, starts, mask), jac=True, method="L-BFGS-B")
        return result.x

    def log_likelihood(self, weights: np.ndarray, features: np.ndarray, hit: np.ndarray, starts: np.ndarray) -> float:
        """当たった組の確率の対数の合計（罰則なし。学習に使っていない区切りでの当たり具合を比べるのに使う）。"""
        likelihood, _ = self._likelihood(weights, features, hit, starts)
        return likelihood

    def _loss(self, weights: np.ndarray, features: np.ndarray, hit: np.ndarray, starts: np.ndarray,
              mask: np.ndarray) -> tuple[float, np.ndarray]:
        """負の（対数尤度 − 罰則）と、その勾配。"""
        likelihood, gradient = self._likelihood(weights, features, hit, starts)
        penalty = self._penalty * float(np.sum(mask * weights ** 2))
        return -(likelihood - penalty), -(gradient - 2.0 * self._penalty * mask * weights)

    def _likelihood(self, weights: np.ndarray, features: np.ndarray, hit: np.ndarray, starts: np.ndarray) -> tuple[float, np.ndarray]:
        sizes = np.diff(np.r_[starts, len(features)])
        score = features @ weights
        top = np.maximum.reduceat(score, starts)
        exponent = np.exp(score - np.repeat(top, sizes))
        total = np.add.reduceat(exponent, starts)
        hits = np.add.reduceat(hit.astype(float), starts)
        likelihood = float(score[hit].sum() - (hits * (np.log(total) + top)).sum())
        share = exponent / np.repeat(total, sizes)
        expected = np.add.reduceat(features * share[:, None], starts)
        gradient = features[hit].sum(axis=0) - (hits[:, None] * expected).sum(axis=0)
        return likelihood, gradient
