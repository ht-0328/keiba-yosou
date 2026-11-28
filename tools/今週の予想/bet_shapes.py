"""買い目の組の集まりを、投票の画面でまとめて買える形（フォーメーション・流し・ボックス）に書き直す。"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from 今週の予想.bet_shape import BetShape
from 今週の予想.ordered_shape_finder import OrderedShapeFinder
from 今週の予想.unordered_shape_finder import UnorderedShapeFinder

#: 着順を区別する組の書き方（``2→7→10``）の、馬番をつなぐ字。区別しない組は ``2-5-10``。
_ORDERED_MARK = "→"
_UNORDERED_MARK = "-"
#: 形をつなぐ字。
_SHAPE_JOIN = " ／ "
#: 馬番1つの買い目（単勝・複勝）をつなぐ字。
_HORSE_JOIN = "・"


class BetShapes:
    """組の書き方（``2-5-10``・``2→7→10``・``3``）の並びを、買う組が変わらないように形にまとめる。

    1つの形でぴったり書ければその形（例 ``フォーメーション 10 − 2・6・7 − 1・2・5・6・7・11・16``）。書けなければ、いちばん多くの組に
    入っている馬（着順を区別する券種は、その着順の馬）で分けて、分けたものをそれぞれ形にする。どの形にもならない組は1点ずつ書く。
    単勝・複勝は馬番を並べるだけ。同じ番号が重なる組（枠連の 1-1）がある券種は、まとめずに1点ずつ書く。
    """

    def __init__(self) -> None:
        self._unordered = UnorderedShapeFinder()
        self._ordered = OrderedShapeFinder()

    def of(self, labels: Sequence[str]) -> list[BetShape]:
        """``labels`` は1点ごとの組の書き方（同じ券種のもの）。"""
        if not labels:
            return []
        ordered = any(_ORDERED_MARK in label for label in labels)
        combos = [tuple(int(horse) for horse in label.split(_ORDERED_MARK if ordered else _UNORDERED_MARK)) for label in labels]
        if len(combos[0]) == 1:
            return [BetShape(_HORSE_JOIN.join(labels), len(labels))]
        if any(len(set(combo)) != len(combo) for combo in combos):
            return [BetShape(label, 1) for label in labels]
        return self._split(frozenset(combos if ordered else map(frozenset, combos)), ordered)

    def text(self, labels: Sequence[str]) -> str:
        """1点の額が同じ買い目の書き方。形が2つ以上なら、形ごとに点数を添える。"""
        shapes = self.of(labels)
        if len(shapes) == 1:
            return shapes[0].text
        return _SHAPE_JOIN.join(f"{shape.text}（{shape.points}点）" for shape in shapes)

    def staked_text(self, staked: Sequence[tuple[str, int]]) -> str:
        """1点ごとに額の違う買い目（組の書き方, 金額）の書き方。同じ額の組だけを形にまとめる（額の大きい順）。

        例: ``フォーメーション 1着 2 → 2着 1・7 → 3着 1・6・7・10・11 各 100円（8点）``・``1-2 1,200円 ／ 2-7 700円``。
        """
        amounts = sorted({yen for _, yen in staked}, reverse=True)
        shapes = [(shape, yen) for yen in amounts for shape in self.of([label for label, staked_yen in staked if staked_yen == yen])]
        return _SHAPE_JOIN.join(f"{shape.text} 各 {yen:,}円（{shape.points}点）" if shape.points > 1 else f"{shape.text} {yen:,}円"
                                for shape, yen in shapes)

    def _split(self, combos: frozenset, ordered: bool) -> list[BetShape]:
        found = (self._ordered if ordered else self._unordered).find(combos)
        if found is not None:
            return [BetShape(found, len(combos))]
        group = _ordered_group(combos) if ordered else _unordered_group(combos)
        return [*self._split(group, ordered), *self._split(combos - group, ordered)]


def _ordered_group(combos: frozenset) -> frozenset:
    """馬が分かれる最初の着順で、いちばん多くの組に入っている馬の組（同じ数なら馬番の小さいほう）。"""
    place = next(index for index in range(len(next(iter(combos)))) if len({combo[index] for combo in combos}) > 1)
    counts = Counter(combo[place] for combo in combos)
    horse = min(counts, key=lambda number: (-counts[number], number))
    return frozenset(combo for combo in combos if combo[place] == horse)


def _unordered_group(combos: frozenset) -> frozenset:
    """全部の組に入っている馬を除いて、いちばん多くの組に入っている馬の組（同じ数なら馬番の小さいほう）。"""
    common = frozenset.intersection(*combos)
    counts = Counter(horse for combo in combos for horse in combo - common)
    horse = min(counts, key=lambda number: (-counts[number], number))
    return frozenset(combo for combo in combos if horse in combo)
