"""着順を区別する券種（馬単・3連単）の組の集まりを、1つの形で書けるか調べる。"""

from __future__ import annotations

from collections.abc import Iterable
from itertools import combinations, permutations, product

#: 馬番をつなぐ字と、着順をつなぐ字。
_JOIN = "・"
_ARROW = " → "
#: 着順の名前（フォーメーションの列の頭に付ける）。
_PLACES: tuple[str, ...] = ("1着", "2着", "3着")

Combo = tuple[int, ...]


class OrderedShapeFinder:
    """組の集まりが、ボックス・マルチ・流し・フォーメーションのどれか1つとぴったり同じなら、その書き方を返す（同じでなければ None）。

    例: 3連単の 2→7→10・2→1→10・2→7→1・2→1→7 は ``フォーメーション 1着 2 → 2着 1・7 → 3着 1・7・10``。
    馬単の 2→7・2→1 は ``1着流し 2 → 1・7``。
    """

    def find(self, combos: frozenset[Combo]) -> str | None:
        horses = sorted({horse for combo in combos for horse in combo})
        size = len(next(iter(combos)))
        if len(combos) == 1:
            return "→".join(str(horse) for horse in next(iter(combos)))
        if combos == frozenset(permutations(horses, size)):
            return f"ボックス {_numbers(horses)}"
        return self._multi(combos, horses, size) or self._formation(combos, size)

    @staticmethod
    def _multi(combos: frozenset[Combo], horses: list[int], size: int) -> str | None:
        """軸の馬（全部の組に入っている馬）と相手で作る組の、着順の全部の並び。"""
        axes = [horse for horse in horses if all(horse in combo for combo in combos)]
        partners = [horse for horse in horses if horse not in axes]
        if not axes or len(axes) >= size:
            return None
        made = frozenset(order for picked in combinations(partners, size - len(axes)) for order in permutations((*axes, *picked)))
        if made != combos:
            return None
        name = "マルチ" if size == 2 else f"軸{len(axes)}頭マルチ"
        return f"{name} 軸 {_numbers(axes)} − 相手 {_numbers(partners)}"

    @staticmethod
    def _formation(combos: frozenset[Combo], size: int) -> str | None:
        """着順ごとの馬の集まりから1頭ずつ選んだ組の全部。馬単で1着か2着が1頭なら、流しと書く。"""
        columns = [sorted({combo[place] for combo in combos}) for place in range(size)]
        if frozenset(picked for picked in product(*columns) if len(set(picked)) == size) != combos:
            return None
        if size == 2 and len(columns[0]) == 1:
            return f"1着流し {columns[0][0]}{_ARROW}{_numbers(columns[1])}"
        if size == 2 and len(columns[1]) == 1:
            return f"2着流し {_numbers(columns[0])}{_ARROW}{columns[1][0]}"
        return "フォーメーション " + _ARROW.join(f"{place} {_numbers(column)}" for place, column in zip(_PLACES, columns, strict=False))


def _numbers(horses: Iterable[int]) -> str:
    return _JOIN.join(str(horse) for horse in horses)
