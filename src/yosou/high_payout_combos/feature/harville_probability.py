"""1着の確率から、Harville の式で組の確率を出す。"""

from __future__ import annotations

from itertools import permutations

import numpy as np

from .material_names import FLOOR


class HarvilleProbability:
    """1着の確率（レースで合計 1 にそろえた値）から、組の確率を出す。

    a→b の確率 = w_a × w_b ÷ (1 − w_a)。a→b→c はさらに × w_c ÷ (1 − w_a − w_b)。割る数の下限は 1e-9。
    例: 1着の確率が 0.5・0.3・0.2 の3頭なら、1→2 は 0.5 × 0.3 ÷ 0.5 = 0.3、1→2→3 は 0.3 × 0.2 ÷ 0.2 = 0.3。
    レースの中でそろえ直さない。
    """

    def in_order(self, shares: np.ndarray) -> np.ndarray:
        """``shares`` は行 × 組の馬（2頭か3頭。着順の並び）の1着の確率。その着順どおりに入る確率（馬単・3連単）。"""
        first, second = shares[:, 0], shares[:, 1]
        top_two = first * second / np.clip(1.0 - first, FLOOR, None)
        if shares.shape[1] == 2:
            return top_two
        return top_two * shares[:, 2] / np.clip(1.0 - first - second, FLOOR, None)

    def any_order(self, shares: np.ndarray) -> np.ndarray:
        """組の馬が、並びを問わずに上位を占める確率（馬連・3連複）。全部の並びの ``in_order`` の和。"""
        orders = permutations(range(shares.shape[1]))
        return np.sum([self.in_order(shares[:, list(order)]) for order in orders], axis=0)

    def pairs_in_top3(self, race_shares: np.ndarray) -> np.ndarray:
        """1レースの全頭の1着の確率（頭数ぶんの1次元）から、2頭とも3着以内に入る確率（頭数 × 頭数。ワイド）。

        i→j→k の確率を全部の i・j・k で作り、i・j を含む3頭の組の6つの並びを、3頭目 k について足す。対角（同じ馬どうし）は 0。
        """
        first = race_shares[:, None, None]
        second = race_shares[None, :, None]
        third = race_shares[None, None, :]
        in_order = first * second / np.clip(1.0 - first, FLOOR, None) * third / np.clip(1.0 - first - second, FLOOR, None)
        same = np.arange(len(race_shares))
        in_order[same, same, :] = 0.0
        in_order[same, :, same] = 0.0
        in_order[:, same, same] = 0.0
        any_order = np.sum([in_order.transpose(axes) for axes in permutations(range(3))], axis=0)
        return any_order.sum(axis=2)
