"""着順を区別しない券種（馬連・ワイド・3連複）の組の集まりを、1つの形で書けるか調べる。"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from itertools import combinations, product

#: 馬番をつなぐ字と、列をつなぐ字。
_JOIN = "・"
_COLUMN = " − "
#: フォーメーションの列（最後の列を除く）を総当たりで探す頭数の上限（最後の列は、ほかの列から決まる）。
_MAX_COLUMN = 4
#: 3列のフォーメーションで調べる、1列目と2列目の候補の組の数の上限（超えたら探さない）。
_MAX_PAIRS = 40000

Combo = frozenset[int]


class UnorderedShapeFinder:
    """組の集まりが、ボックス・流し・フォーメーションのどれか1つとぴったり同じなら、その書き方を返す（同じでなければ None）。

    例: 3連複の 2-5-10・5-7-10・2-7-10 は ``軸1頭流し 軸 10 − 相手 2・5・7``。
    1-2-10・1-7-10・2-6-10・6-7-10 は ``フォーメーション 10 − 1・6 − 2・7``。
    """

    def find(self, combos: frozenset[Combo]) -> str | None:
        horses = sorted(frozenset().union(*combos))
        size = len(next(iter(combos)))
        if len(combos) == 1:
            return "-".join(str(horse) for horse in horses)
        if combos == _all_of(horses, size):
            return f"ボックス {_numbers(horses)}"
        common = sorted(frozenset.intersection(*combos))
        return self._pairs(combos, horses, common) if size == 2 else self._trios(combos, horses, common)

    def _pairs(self, combos: frozenset[Combo], horses: list[int], common: list[int]) -> str | None:
        if common:
            return f"流し 軸 {common[0]}{_COLUMN}相手 {_numbers(_others(horses, common))}"
        columns = self._two_columns(combos, horses)
        return f"フォーメーション {_columns(columns)}" if columns else None

    def _trios(self, combos: frozenset[Combo], horses: list[int], common: list[int]) -> str | None:
        partners = _others(horses, common)
        if len(common) == 2:
            return f"軸2頭流し 軸 {_numbers(common)}{_COLUMN}相手 {_numbers(partners)}"
        if not common:
            columns = self._three_columns(combos, horses)
            return f"フォーメーション {_columns(columns)}" if columns else None
        rest = frozenset(combo - frozenset(common) for combo in combos)
        if rest == _all_of(partners, 2):
            return f"軸1頭流し 軸 {common[0]}{_COLUMN}相手 {_numbers(partners)}"
        columns = self._two_columns(rest, partners)
        return f"フォーメーション {common[0]}{_COLUMN}{_columns(columns)}" if columns else None

    @staticmethod
    def _two_columns(pairs: frozenset[Combo], horses: list[int]) -> tuple[list[int], ...] | None:
        """``pairs`` が「1列目のどれか − 2列目のどれか」の全部とぴったり同じになる2列（1列目の少ないものから探す）。"""
        for first in _subsets(horses):
            second = [horse for horse in horses if _fits(horse, [first], pairs)]
            if _expand([first, second]) == pairs:
                return list(first), second
        return None

    @staticmethod
    def _three_columns(trios: frozenset[Combo], horses: list[int]) -> tuple[list[int], ...] | None:
        """``trios`` が「1列目 − 2列目 − 3列目」の全部とぴったり同じになる3列。どの組にも1頭は入っている集まりだけを列の候補にする。"""
        candidates = [subset for subset in _subsets(horses) if all(combo & frozenset(subset) for combo in trios)]
        if len(candidates) ** 2 > _MAX_PAIRS:
            return None
        for first, second in product(candidates, candidates):
            third = [horse for horse in horses if len(first) <= len(second) and _fits(horse, [first, second], trios)]
            if third and _expand([first, second, third]) == trios:
                return list(first), list(second), third
        return None


def _subsets(horses: list[int]) -> Iterator[tuple[int, ...]]:
    """1頭以上 ``_MAX_COLUMN`` 頭以下の集まりを、頭数の少ない順に。"""
    return (subset for size in range(1, min(len(horses), _MAX_COLUMN) + 1) for subset in combinations(horses, size))


def _fits(horse: int, columns: list[tuple[int, ...]], combos: frozenset[Combo]) -> bool:
    """``horse`` を最後の列に入れてよいか（ほかの列の馬と作る組が、1つ以上あって、全部 ``combos`` にある）。"""
    made = _expand([*columns, (horse,)])
    return bool(made) and made <= combos


def _expand(columns: list[Iterable[int]]) -> frozenset[Combo]:
    """各列から1頭ずつ選んだ組（同じ馬が重なる選び方は除く）。"""
    return frozenset(frozenset(picked) for picked in product(*columns) if len(set(picked)) == len(columns))


def _all_of(horses: list[int], size: int) -> frozenset[Combo]:
    return frozenset(frozenset(picked) for picked in combinations(horses, size))


def _others(horses: list[int], removed: list[int]) -> list[int]:
    return [horse for horse in horses if horse not in removed]


def _numbers(horses: Iterable[int]) -> str:
    return _JOIN.join(str(horse) for horse in horses)


def _columns(columns: tuple[list[int], ...]) -> str:
    return _COLUMN.join(_numbers(column) for column in columns)
