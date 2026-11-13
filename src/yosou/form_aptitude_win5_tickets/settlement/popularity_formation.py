"""比べる相手 (2): 人気だけで選ぶ買い目。"""

from __future__ import annotations

import math
from collections.abc import Sequence

from ..formation import Formation


class PopularityFormation:
    """各レースの人気の上位から、予算に収まるいちばん大きいフォーメーション（各レースの頭数をなるべくそろえる）を作る（設計書 16 の 5.）。

    全レース1頭から始め、頭数のいちばん少ないレース（同じなら前のレース）に1頭ずつ足していく。足すと予算を超えるか、
    そのレースの頭数を超えるレースには足さない。どのレースにも足せなくなったら終わり。
    """

    def of(self, popularity: Sequence[Sequence[int]], budget: int) -> Formation:
        """``popularity`` は5レースの、人気の順に並べた馬番。"""
        sizes = [1] * len(popularity)
        while (leg := self._next_leg(sizes, popularity, budget)) is not None:
            sizes[leg] += 1
        return Formation(tuple(tuple(numbers[:size]) for numbers, size in zip(popularity, sizes, strict=True)))

    def _next_leg(self, sizes: list[int], popularity: Sequence[Sequence[int]], budget: int) -> int | None:
        """次に1頭足すレース。足せるレースが無ければ None。"""
        candidates = [leg for leg in range(len(sizes)) if self._can_grow(sizes, leg, popularity, budget)]
        if not candidates:
            return None
        return min(candidates, key=lambda leg: (sizes[leg], leg))

    def _can_grow(self, sizes: list[int], leg: int, popularity: Sequence[Sequence[int]], budget: int) -> bool:
        grown = math.prod(sizes) // sizes[leg] * (sizes[leg] + 1)
        return sizes[leg] < len(popularity[leg]) and grown <= budget
