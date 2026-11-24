"""勝つ確率から、着順の並びの確率を作る（強い順に1頭ずつ抜いていく形）。

1着→2着→3着 の確率 = 1着の確率 × 残りの中での2着の確率 × 残りの中での3着の確率。
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import permutations

#: 残りの確率の下限（0 で割らないため）。
_FLOOR = 1e-9


class OrderProbabilities:
    def __init__(self, win: Sequence[float]) -> None:
        self._win = [float(value) for value in win]

    def order(self, first: int, second: int, third: int) -> float:
        """並びの位置（0 始まり）で指した3頭が、この順に 1〜3着になる確率。"""
        win = self._win
        rest_after_first = max(1 - win[first], _FLOOR)
        rest_after_second = max(1 - win[first] - win[second], _FLOOR)
        return win[first] * win[second] / rest_after_first * win[third] / rest_after_second

    def top3(self) -> list[float]:
        """各馬が3着以内に入る確率（3頭以下のレースは全部 1）。"""
        count = len(self._win)
        if count <= 3:
            return [1.0] * count
        totals = [0.0] * count
        for first, second, third in permutations(range(count), 3):
            probability = self.order(first, second, third)
            for index in (first, second, third):
                totals[index] += probability
        return [min(total, 1.0) for total in totals]
