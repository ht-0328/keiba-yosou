"""レースの中で合計1になる確率を作る。"""

from __future__ import annotations

import numpy as np


class RaceSoftmax:
    """馬ごとの点数を、レースの中で合計1になる確率に直す。

    1頭ずつ独立に「勝つか」を当てる学習では、同じレースの馬の確率を足しても1にならない。
    馬券の期待値を計算するには、レースの中で合計1になっている必要がある。

    ``race_index`` は行ごとのレースの番号で、同じレースの行が続いて並んでいること（ソート済み）が前提。
    """

    def __init__(self, race_index: np.ndarray) -> None:
        self._race_index = race_index.astype(np.int64)
        self._race_count = int(self._race_index.max()) + 1
        self._first_row = np.searchsorted(self._race_index, np.arange(self._race_count))

    @property
    def race_count(self) -> int:
        return self._race_count

    def to_probability(self, score: np.ndarray) -> np.ndarray:
        """点数 → レース内で合計1の確率。大きい点数を引いてから exp を取り、桁あふれを避ける。"""
        largest = np.maximum.reduceat(score, self._first_row)
        exponent = np.exp(score - largest[self._race_index])
        total = np.bincount(self._race_index, weights=exponent, minlength=self._race_count)
        return exponent / total[self._race_index]
