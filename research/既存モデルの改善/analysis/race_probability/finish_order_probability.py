"""勝率から、着順の並びの確率を出す（Stern の補正つき Harville の式）。"""

from __future__ import annotations

import numpy as np

#: 割り算の分母が 0 に近くなるのを防ぐ下限。
_FLOOR = 1e-12


class FinishOrderProbability:
    """1レースの勝率 ``p``（馬の並びの配列。合計 1）から、1着・2着・3着の並びの確率を出す。

    Harville の式は「1着が決まったら、残りの馬の中で勝率の比で2着を決める。3着も同じ」と考えるが、実際より
    人気馬が2着・3着に入る確率を高く見積もる。Stern の補正では、2着を決めるときの重みを ``p^λ``、3着を決めるときの
    重みを ``p^μ``（λ・μ は 1 より小さい）にして、人気馬の寄りを弱める。λ = μ = 1 なら Harville の式そのもの。

    例: 勝率 0.5・0.3・0.2 の3頭で λ = 1 なら、2頭目が1着・1頭目が2着の確率は 0.3 × 0.5 ÷ (1 − 0.3) ≒ 0.21。
    """

    def __init__(self, lam: float = 1.0, mu: float = 1.0) -> None:
        self._lam = lam
        self._mu = mu

    def ordered_pair(self, p: np.ndarray) -> np.ndarray:
        """``[i, j]`` = i が1着・j が2着の確率。同じ馬の組は 0。"""
        second = np.power(p, self._lam)
        table = p[:, None] * second[None, :] / np.clip(second.sum() - second[:, None], _FLOOR, None)
        np.fill_diagonal(table, 0.0)
        return table

    def ordered_triple(self, p: np.ndarray) -> np.ndarray:
        """``[i, j, k]`` = i が1着・j が2着・k が3着の確率。同じ馬が重なる組は 0。"""
        third = np.power(p, self._mu)
        remaining = np.clip(third.sum() - third[:, None] - third[None, :], _FLOOR, None)
        table = self.ordered_pair(p)[:, :, None] * third[None, None, :] / remaining[:, :, None]
        index = np.arange(len(p))
        table[index, :, index] = 0.0
        table[:, index, index] = 0.0
        table[index, index, :] = 0.0
        return table

    def quinella(self, p: np.ndarray) -> np.ndarray:
        """``[i, j]`` = i と j が1着・2着を占める確率（順不同。対称な表）。"""
        pair = self.ordered_pair(p)
        return pair + pair.T

    def trio(self, p: np.ndarray) -> np.ndarray:
        """``[i, j, k]`` = i・j・k が1〜3着を占める確率（順不同。どの並びの要素も同じ値）。"""
        table = self.ordered_triple(p)
        return (table + table.transpose(0, 2, 1) + table.transpose(1, 0, 2)
                + table.transpose(1, 2, 0) + table.transpose(2, 0, 1) + table.transpose(2, 1, 0))

    def top_two(self, p: np.ndarray) -> np.ndarray:
        """``[i]`` = i が2着以内に入る確率。"""
        return self.quinella(p).sum(axis=1)

    def top_three(self, p: np.ndarray) -> np.ndarray:
        """``[i]`` = i が3着以内に入る確率。"""
        return self.trio(p).sum(axis=(1, 2)) / 2.0

    def wide(self, p: np.ndarray) -> np.ndarray:
        """``[i, j]`` = i と j がどちらも3着以内に入る確率。"""
        return self.trio(p).sum(axis=2)
