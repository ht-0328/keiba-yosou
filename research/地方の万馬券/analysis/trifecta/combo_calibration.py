"""組の確率の直し: 「当たった／外れた」を目的に、予想の組の確率と市場の組の確率の対数で当てはめるロジスティック回帰（切片つき）。

係数の読み方: log p の係数が 1・log m の係数が 0 なら予想の確率がそのまま正しく、逆なら市場の確率がそのまま正しい。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

_FLOOR = 1e-9
#: 係数の名前（戻りの順）。
COEFFICIENTS: tuple[str, ...] = ("切片", "log p の係数", "log m の係数")


@dataclass(frozen=True)
class ComboCalibration:
    """``fit`` で係数を求め、``apply`` で直した確率を出す。ニュートン法（外部ライブラリは使わない）。"""

    iterations: int = 30

    def fit(self, probability: pd.Series, market: pd.Series, hit: pd.Series) -> np.ndarray:
        design = self._design(probability, market)
        y = hit.to_numpy(dtype=float)
        beta = np.zeros(design.shape[1])
        for _ in range(self.iterations):
            p = self._sigmoid(design @ beta)
            gradient = design.T @ (p - y)
            hessian = (design * (p * (1.0 - p))[:, None]).T @ design + 1e-9 * np.eye(design.shape[1])
            beta = beta - np.linalg.solve(hessian, gradient)
        return beta

    def apply(self, beta: np.ndarray, probability: pd.Series, market: pd.Series) -> np.ndarray:
        return self._sigmoid(self._design(probability, market) @ beta)

    def _design(self, probability: pd.Series, market: pd.Series) -> np.ndarray:
        return np.column_stack([
            np.ones(len(probability)),
            np.log(probability.to_numpy(dtype=float).clip(_FLOOR)),
            np.log(market.to_numpy(dtype=float).clip(_FLOOR)),
        ])

    def _sigmoid(self, z: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-z))
