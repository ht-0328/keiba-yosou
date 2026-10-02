"""レースの中で、どの馬が勝つかを学ぶ（条件付きロジット）。"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize


class RaceStrengthModel:
    """同じレースの馬どうしを比べて「どの馬が勝つか」を学ぶ（条件付きロジット）。出る勝率はレース内で合計 1 になる。

    材料（``features``）の重みを、勝った馬に付けた勝率の log が最大になるように決める。
    例: 材料を「log(オッズから見た勝率)」と「予想モデルの上げ下げ」にすると、重みは「市場をどれだけ信じるか」と
    「モデルの上げ下げをどれだけ効かせるか」になる。最初の材料の重み 1・ほかは 0 から探す（市場そのまま）。
    ``ridge`` は重みを 0 に寄せる強さ（わずかな凹凸に引きずられないように）。
    """

    def __init__(self, ridge: float = 1e-4, max_iterations: int = 300) -> None:
        self._ridge = ridge
        self._max_iterations = max_iterations
        self._weights: np.ndarray | None = None

    @property
    def weights(self) -> np.ndarray:
        if self._weights is None:
            raise RuntimeError("まだ学習していません（fit を先に呼んでください）")
        return self._weights

    def fit(self, features: np.ndarray, race_ids: pd.Series, won: np.ndarray) -> RaceStrengthModel:
        """``won`` は1着なら 1。1着のいないレースは、勝った馬の log に何も足さない（重みには効かない）。

        ``features`` と ``won`` に欠損値・無限大があると勾配が NaN になり、最適化が1歩も進まずに出発点
        （市場そのまま）を返してしまうので、先に ``ValueError`` にする。学べなかったときも ``RuntimeError`` にする。
        """
        if not (np.isfinite(features).all() and np.isfinite(won).all()):
            raise ValueError("材料か1着の列に、欠損値か無限大があります（着順の無い馬は won を 0 にしてください）")
        codes, races = pd.factorize(race_ids, sort=False)
        race_count = len(races)

        def objective(weights: np.ndarray) -> tuple[float, np.ndarray]:
            probability = self._softmax(features @ weights, codes, race_count)
            loss = -np.log(np.clip(probability[won == 1], 1e-12, None)).sum() / race_count
            gradient = -(features.T @ (won - probability * self._has_winner(won, codes, race_count))) / race_count
            return loss + self._ridge * weights @ weights, gradient + 2 * self._ridge * weights

        start = np.zeros(features.shape[1])
        start[0] = 1.0
        result = minimize(objective, start, jac=True, method="L-BFGS-B", options={"maxiter": self._max_iterations})
        if not np.isfinite(result.x).all() or result.nit == 0:
            raise RuntimeError(f"勝率の重みを学べませんでした: {result.message}")
        self._weights = result.x
        return self

    def predict(self, features: np.ndarray, race_ids: pd.Series) -> np.ndarray:
        """レース内で合計 1 になる勝率。"""
        codes, races = pd.factorize(race_ids, sort=False)
        return self._softmax(features @ self.weights, codes, len(races))

    def _softmax(self, score: np.ndarray, codes: np.ndarray, race_count: int) -> np.ndarray:
        """レースごとの softmax。"""
        top = np.full(race_count, -np.inf)
        np.maximum.at(top, codes, score)
        exponent = np.exp(score - top[codes])
        total = np.bincount(codes, weights=exponent, minlength=race_count)
        return exponent / total[codes]

    def _has_winner(self, won: np.ndarray, codes: np.ndarray, race_count: int) -> np.ndarray:
        """行ごとに、そのレースに1着の馬がいるか（1 か 0）。勾配の計算で、1着のいないレースを外す。"""
        winners = np.bincount(codes, weights=won.astype(float), minlength=race_count)
        return (winners[codes] > 0).astype(float)
