"""印の組み合わせで決める、1つの券種の買い目のルール。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from itertools import chain, product

from 馬券の買い方の検証.analysis.ticket import TicketType

from .mark import Mark

#: 着順どおりに当てる券種（並びを入れ替えると別の買い目になる）。
_ORDERED = (TicketType.EXACTA, TicketType.TRIFECTA)


@dataclass(frozen=True)
class MarkRule:
    """印の組み合わせで決める、1つの券種の買い目のルール。

    - ``legs``: 1頭目・2頭目・3頭目にそれぞれ入れる印（フォーメーション）。同じ馬は2回使わない。
    - ``orders``: 着順のある券種で、選んだ馬（1頭目・2頭目・3頭目）をどの着順の並びで買うか。
      例: 3連単の (0, 1, 2) はそのまま、(1, 0, 2) は1着と2着の入れ替え（表裏）、(0, 2, 1) は2着と3着の入れ替え。
      着順の無い券種は (0, 1, …) の1つだけでよい（並びは馬番の小さい順にそろえる）。
    - ``cover``: 押さえ（◎が危ういときだけ買う）のルールか。

    例: 馬連で legs=((◎,), (○, ▲, △)) なら、◎-○・◎-▲・◎-△（△は3頭）の5点。
    """

    ticket: TicketType
    legs: tuple[tuple[Mark, ...], ...]
    orders: tuple[tuple[int, ...], ...]
    cover: bool = False

    def combos(self, horses_of: Mapping[Mark, tuple[int, ...]]) -> list[tuple[int, ...]]:
        """印 → その印の馬番の並び から、買い目（馬番の並び）を作る。重なりは1つにまとめる。"""
        pools = [tuple(chain.from_iterable(horses_of.get(mark, ()) for mark in leg)) for leg in self.legs]
        picks = [pick for pick in product(*pools) if len(set(pick)) == len(pick)]
        return sorted({self._arrange(pick, order) for pick in picks for order in self.orders})

    def _arrange(self, pick: tuple[int, ...], order: tuple[int, ...]) -> tuple[int, ...]:
        arranged = tuple(pick[position] for position in order)
        return arranged if self.ticket in _ORDERED else tuple(sorted(arranged))
