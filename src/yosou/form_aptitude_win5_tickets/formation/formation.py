"""WIN5 のフォーメーションを表す値。"""

from __future__ import annotations

import itertools
import math
from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class Formation:
    """対象レースごとに選んだ馬番の並び（発売の順に5つ）。点数は各レースの頭数のかけ算（設計書 02 の「フォーメーション」）。"""

    legs: tuple[tuple[int, ...], ...]

    @property
    def points(self) -> int:
        """点数（1点 = 1組）。"""
        return math.prod(len(picks) for picks in self.legs)

    @property
    def sizes(self) -> tuple[int, ...]:
        """各レースの頭数。"""
        return tuple(len(picks) for picks in self.legs)

    def combos(self) -> Iterator[tuple[int, ...]]:
        """全部の組（5頭の馬番の並び）。"""
        return itertools.product(*self.legs)

    def contains(self, combo: tuple[int, ...]) -> bool:
        """``combo`` がこのフォーメーションの組の1つか。"""
        return len(combo) == len(self.legs) and all(number in picks for number, picks in zip(combo, self.legs, strict=True))

    def sizes_text(self) -> str:
        """``2×5×2×1×5`` の形。"""
        return "×".join(str(size) for size in self.sizes)
