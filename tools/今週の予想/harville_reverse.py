"""1着の確率から、Harville の考え方で「裏が当たる確率」（1着が相手のどれかで、◎ が2着か3着）を出す。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


class HarvilleReverse:
    """馬ごとの1着の確率（合計 1 にそろえる）から、1着が ``partners`` のどれかで、``top`` が2着か3着になる確率を出す。

    Harville の考え方: 1着が決まったら、残りの馬の1着の確率を合計 1 にそろえ直したものを2着の確率にする（3着も同じ）。
    """

    def of(self, win: np.ndarray, top: int, partners: Sequence[int]) -> float:
        """``win`` は馬ごとの1着の確率（並びの位置で馬を指す）、``top`` は ◎ の位置、``partners`` は相手の位置。"""
        share = np.asarray(win, dtype=float)
        share = share / share.sum()
        total = 0.0
        for first in partners:
            rest = 1.0 - share[first]
            total += share[first] * share[top] / rest   # 相手 → ◎
            for second in range(len(share)):
                if second in (first, top):
                    continue
                total += share[first] * share[second] / rest * share[top] / (rest - share[second])   # 相手 → ほかの馬 → ◎
        return float(total)
