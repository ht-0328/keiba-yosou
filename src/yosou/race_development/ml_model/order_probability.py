"""1着の確率から、1〜3着の並びの確率を出す（Harville の式）。"""

from __future__ import annotations

import itertools
from functools import lru_cache

import numpy as np

#: 3着まで。
_PLACES = 3


class OrderProbability:
    """1レースの1着の確率（合計 1）から、3連単の全部の並びの確率と、各馬の 2着以内・3着以内の確率を出す（設計書 03 の 5・10 の 10.）。

    i が1着のとき j が2着の確率は ``p_j^λ ÷（i を除いた全馬の p^λ の合計）``、i・j が1・2着のとき k が3着の確率も同じ形。
    λ（ならしの指数）が 1 なら Harville の式のまま。1 より小さいと、2着・3着の確率が人気のない馬にも配られる。
    """

    def trifecta(self, win: np.ndarray, lam: float) -> tuple[np.ndarray, np.ndarray]:
        """（並び, 確率）。並びは 行数 × 3 の、1着・2着・3着の馬の位置（``win`` の何番目か）。確率の合計は 1。

        3頭に満たないレースは、空の並びを返す。
        """
        p = np.asarray(win, dtype="float64")
        orders = _permutations(len(p))
        if len(orders) == 0:
            return orders, np.zeros(0)
        q = p ** lam
        total = q.sum()
        first, second, third = orders[:, 0], orders[:, 1], orders[:, 2]
        second_given_first = q[second] / (total - q[first])
        third_given_two = q[third] / (total - q[first] - q[second])
        return orders, p[first] * second_given_first * third_given_two

    def places(self, win: np.ndarray, lam: float) -> np.ndarray:
        """各馬の 1着・2着以内・3着以内の確率（頭数 × 3）。3頭に満たないレースは、1着の確率だけ入れ、ほかは欠損値。"""
        p = np.asarray(win, dtype="float64")
        orders, probability = self.trifecta(p, lam)
        if len(orders) == 0:
            return np.column_stack([p, np.full(len(p), np.nan), np.full(len(p), np.nan)])
        by_place = [np.bincount(orders[:, place], weights=probability, minlength=len(p)) for place in range(_PLACES)]
        return np.column_stack([by_place[0], by_place[0] + by_place[1], by_place[0] + by_place[1] + by_place[2]])


@lru_cache(maxsize=32)
def _permutations(count: int) -> np.ndarray:
    """0〜count−1 から3つを選んで並べる全部の並び（頭数ごとに1回だけ作る）。"""
    if count < _PLACES:
        return np.zeros((0, _PLACES), dtype=int)
    return np.array(list(itertools.permutations(range(count), _PLACES)), dtype=int)
