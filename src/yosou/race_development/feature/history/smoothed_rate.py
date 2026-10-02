"""走った数の少ない馬の割合を、全体の割合に寄せる。"""

from __future__ import annotations

import numpy as np

#: 全体の割合に寄せる強さ α（設計書 09 の K の「平滑化」。初期値）。
SMOOTHING_ALPHA = 3.0


class SmoothedRate:
    """``(当たった数 + α × 全体の割合) ÷ (数えた走の数 + α)``（設計書 09 の K）。

    1走して1回先頭だった馬を「先頭率 100%」と見ないため。走った数が 0 の馬は、全体の割合になる。
    """

    def __init__(self, alpha: float = SMOOTHING_ALPHA) -> None:
        self._alpha = alpha

    def of(self, hits: np.ndarray, count: np.ndarray, prior: np.ndarray) -> np.ndarray:
        """どれも同じ長さの配列。"""
        return (hits + self._alpha * prior) / (count + self._alpha)
