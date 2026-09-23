"""勝率から、馬連・ワイド・3連複の的中確率を計算する（Stern 補正つき Harville）。"""
from __future__ import annotations

import numpy as np


class SternProbabilities:
    """1レースの勝率から、組み合わせ券種の的中確率を作る。

    Harville は「1着が決まったら、残りを勝率の比で割り振る」と考えるが、実際より人気馬を高く見積もる。
    Stern の補正は、2着・3着を決めるときの勝率を ``p^λ``・``p^μ``（λ, μ < 1）に置き換えて、
    人気馬の寄りを弱める。λ・μ は過去の着順から推定する。
    """

    def __init__(self, lam: float, mu: float) -> None:
        self._lam = lam
        self._mu = mu

    def ordered_pair(self, p: np.ndarray) -> np.ndarray:
        """``[i, j]`` = i が1着・j が2着になる確率。対角は 0。"""
        s = np.power(p, self._lam)
        table = p[:, None] * s[None, :] / np.clip(s.sum() - s[:, None], 1e-12, None)
        np.fill_diagonal(table, 0.0)
        return table

    def ordered_triple(self, p: np.ndarray) -> np.ndarray:
        """``[i, j, k]`` = i が1着・j が2着・k が3着になる確率。同じ馬が重なる要素は 0。"""
        t = np.power(p, self._mu)
        pair = self.ordered_pair(p)
        remaining = np.clip(t.sum() - t[:, None] - t[None, :], 1e-12, None)
        table = pair[:, :, None] * t[None, None, :] / remaining[:, :, None]
        size = len(p)
        index = np.arange(size)
        table[index, :, index] = 0.0
        table[:, index, index] = 0.0
        table[index, index, :] = 0.0
        return table

    def quinella(self, p: np.ndarray) -> np.ndarray:
        """``[i, j]`` = i と j が1着・2着を占める確率（順不同）。"""
        pair = self.ordered_pair(p)
        return pair + pair.T

    def trio(self, p: np.ndarray) -> np.ndarray:
        """``[i, j, k]`` = i・j・k が1〜3着を占める確率（順不同）。要素は組ごとに同じ値。"""
        table = self.ordered_triple(p)
        return (table + table.transpose(0, 2, 1) + table.transpose(1, 0, 2)
                + table.transpose(1, 2, 0) + table.transpose(2, 0, 1) + table.transpose(2, 1, 0))

    def wide(self, p: np.ndarray) -> np.ndarray:
        """``[i, j]`` = i と j がどちらも3着以内に入る確率。"""
        return self.trio(p).sum(axis=2)

    def top_three(self, p: np.ndarray) -> np.ndarray:
        """``[i]`` = i が3着以内に入る確率。"""
        return self.trio(p).sum(axis=(1, 2)) / 2.0
