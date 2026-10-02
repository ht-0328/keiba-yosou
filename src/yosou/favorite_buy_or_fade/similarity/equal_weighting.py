"""列ごとの重みを付けない。"""

from __future__ import annotations

import numpy as np


class EqualWeighting:
    """列ごとの重みを付けない（どの列も 1。まとまりの重みだけが効く。方針の ``column_weighting`` の ``method = "なし"``）。"""

    def __init__(self) -> None:
        self._weights = np.empty(0)

    def fit(self, matrix: np.ndarray, is_out: np.ndarray | None = None) -> EqualWeighting:
        """``is_out`` は使わない（``AucWeighting`` と同じ呼び方にするため）。"""
        self._weights = np.ones(matrix.shape[1])
        return self

    @property
    def weights(self) -> np.ndarray:
        """列ごとの重み（行列の列と同じ並び）。"""
        return self._weights
