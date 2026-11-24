"""行の重みを付けた対数損失。"""

from __future__ import annotations

import numpy as np

#: 確率を 0 と 1 から離す幅（log 0 にならないように）。
_EDGE = 1e-12


def weighted_log_loss(hit: np.ndarray, probability: np.ndarray, weight: np.ndarray) -> float:
    """重みを付けた対数損失（小さいほど当たっている）。``hit`` は当たったか（1 か 0）、``probability`` は当たる確率、``weight`` は行の重み。

    例: 当たった行に 0.5、外れた行に 0.5 を出していれば log 2 ≒ 0.69。
    """
    clipped = np.clip(probability, _EDGE, 1.0 - _EDGE)
    losses = -(hit * np.log(clipped) + (1 - hit) * np.log(1.0 - clipped))
    return float((weight * losses).sum() / weight.sum())
