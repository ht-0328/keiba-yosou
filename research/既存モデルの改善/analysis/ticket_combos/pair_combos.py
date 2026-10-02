"""馬連・ワイド・馬単の買い目の候補（2頭）。"""

from __future__ import annotations

from itertools import combinations, product

from .combo_groups import HOLE_HOLE, POPULAR_HOLE, POPULAR_POPULAR
from .race_horses import RaceHorses


class PairCombos:
    """2頭の券種の候補。基本は「人気 + 穴」。人気-人気も候補にするが、買うのは期待値のいちばん高い1点だけ
    （絞り込みは ``RaceTicketBuilder``）。荒れそうなレース（``upset``）では、穴-穴の組み合わせも候補にする。

    ``ordered`` が True（馬単）なら、同じ2頭の両方の並び（表裏）を候補にする。
    """

    def __init__(self, ordered: bool) -> None:
        self._ordered = ordered

    def of(self, horses: RaceHorses, upset: bool) -> list[tuple[tuple[int, ...], str]]:
        pairs = [(pair, POPULAR_HOLE) for pair in product(horses.popular, horses.holes)]
        pairs += [(pair, POPULAR_POPULAR) for pair in combinations(horses.popular, 2)]
        pairs += [(pair, HOLE_HOLE) for pair in combinations(horses.holes, 2)] if upset else []
        return [(arranged, group) for pair, group in pairs for arranged in self._arrange(pair)]

    def _arrange(self, pair: tuple[int, int]) -> list[tuple[int, ...]]:
        if self._ordered:
            return [pair, (pair[1], pair[0])]
        return [tuple(sorted(pair))]
