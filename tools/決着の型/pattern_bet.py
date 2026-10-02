"""人気で決める買い目（ボックス・フォーメーション）。「3連複:1,2,3,5,6」「3連単:2/1/6-10」の書き方を読む。"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, permutations, product

from 決着の型.ticket_kind import TicketKind, ticket_kind

#: 券種と人気の区切り、列の区切り、列の中の区切り、範囲の区切り。
_KIND_SEPARATOR, _COLUMN_SEPARATOR, _ITEM_SEPARATOR, _RANGE_SEPARATOR = ":", "/", ",", "-"
_FORMAT_HELP = "券種:人気 の形で書く。ボックスは「3連複:1,2,3,5,6」、フォーメーションは列を / で区切って「3連単:2/1/6-10」"


@dataclass(frozen=True)
class PatternBet:
    """券種と、列ごとの人気の集合。列が1つならボックス、券種の馬の数と同じならフォーメーション。"""

    kind: TicketKind
    columns: tuple[frozenset[int], ...]
    text: str

    def __post_init__(self) -> None:
        if len(self.columns) not in (1, self.kind.horses):
            raise ValueError(f"{self.kind.name} の列は 1つ（ボックス）か {self.kind.horses}つ（フォーメーション）です: {self.text}")
        if self.is_box and len(self.columns[0]) < self.kind.horses:
            raise ValueError(f"{self.kind.name} のボックスには人気を {self.kind.horses}つ以上書いてください: {self.text}")

    @property
    def is_box(self) -> bool:
        return len(self.columns) == 1

    @classmethod
    def parse(cls, text: str) -> "PatternBet":
        """``3連複:1,2,3,5,6`` / ``3連単:2/1/6-10`` / ``ワイド:1/2`` を読む。"""
        kind_text, separator, pops_text = text.strip().partition(_KIND_SEPARATOR)
        if not separator or not pops_text.strip():
            raise ValueError(f"{_FORMAT_HELP}: {text}")
        columns = tuple(frozenset(_parse_column(column)) for column in pops_text.split(_COLUMN_SEPARATOR))
        return cls(ticket_kind(kind_text), columns, text.strip())

    def tickets(self, horses_by_popularity: dict[int, list[int]]) -> set[tuple[int, ...]]:
        """そのレースでの買い目（馬番の組）。人気の無い列があれば、その列の馬が無いぶん組が減る（1頭も居なければ 0 点）。"""
        horse_columns = [sorted(no for pop in column for no in horses_by_popularity.get(pop, ())) for column in self.columns]
        if self.is_box:
            picker = permutations if self.kind.ordered else combinations
            combos = picker(horse_columns[0], self.kind.horses)
        else:
            combos = (combo for combo in product(*horse_columns) if len(set(combo)) == len(combo))
        return {self.kind.canonical(tuple(combo)) for combo in combos}


def _parse_column(text: str) -> list[int]:
    """``1,2,3`` / ``6-10`` / ``1,3-5`` を人気の並びにする。"""
    pops: list[int] = []
    for item in text.split(_ITEM_SEPARATOR):
        low_text, separator, high_text = item.strip().partition(_RANGE_SEPARATOR)
        try:
            low = int(low_text)
            high = int(high_text) if separator else low
        except ValueError:
            raise ValueError(f"{_FORMAT_HELP}: {item}") from None
        if low < 1 or high < low:
            raise ValueError(f"人気は 1 以上で、範囲は小さい順に書いてください: {item}")
        pops.extend(range(low, high + 1))
    return pops
