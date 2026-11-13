"""買い目の形（順位の列の組み合わせ）。"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

from yosou.shared.betting import TicketType

from .payout_floor import PayoutFloor
from .rank_span import RankSpan

#: 形の分け方。「形」はサイトの個々の買い目、「上位5頭BOX」は上位5頭のボックス。
FORM, BOX = "形", "上位5頭BOX"


@dataclass(frozen=True)
class Formation:
    """1つの買い目の形。``columns`` は列（1頭目・2頭目・3頭目）ごとの順位の範囲の集まり。

    組は列ごとの順位の直積から、同じ順位を2度使う組を除いたもの。順番を問わない券種（馬連・ワイド・3連複）は、
    同じ馬の組を1つにまとめる（1位−2〜4位−3〜8位 の「残り」は、この重なりを除くこと）。
    ``floors`` はサイトの集計金額（的中の払戻の下限。複数あれば全部の割合を出す）。
    """

    label: str
    ticket: TicketType
    columns: tuple[tuple[RankSpan, ...], ...]
    floors: tuple[PayoutFloor, ...]
    group: str = FORM

    def __post_init__(self) -> None:
        if len(self.columns) != self.ticket.spec.horse_count:
            raise ValueError(f"{self.label}: 列の数 {len(self.columns)} が券種 {self.ticket.label} の馬の数と合いません")

    @property
    def ordered(self) -> bool:
        """着順を区別する券種か（馬単・3連単）。"""
        return self.ticket.spec.is_ordered

    @property
    def horse_count(self) -> int:
        return len(self.columns)

    def rank_combos(self, field: int) -> list[tuple[int, ...]]:
        """頭数 ``field`` のレースで買う、順位の組（順番を問わない券種は昇順の組）。頭数が足りない順位は使わない。"""
        pools = [sorted({rank for span in column for rank in span.ranks(field)}) for column in self.columns]
        found: dict[tuple[int, ...], None] = {}
        for combo in itertools.product(*pools):
            if len(set(combo)) < len(combo):
                continue
            found.setdefault(combo if self.ordered else tuple(sorted(combo)), None)
        return list(found)
