"""推奨買目の1点（券種・組・オッズ・確率・期待値・金額）。"""

from __future__ import annotations

from dataclasses import dataclass

#: 1点の金額（円）。
STAKE = 100
#: 着順の付く券種（組の表示を → でつなぐ）。ほかは番号の小さい順を - でつなぐ。
ORDERED_TICKETS: frozenset[str] = frozenset({"馬単", "3連単"})


@dataclass(frozen=True)
class Recommendation:
    ticket: str
    #: 馬番（枠連は枠番）の並び。
    numbers: tuple[int, ...]
    #: 買うときのオッズ（複勝・ワイドは幅の真ん中）。
    odds: float
    probability: float
    #: 期待値（確率 × オッズ）。
    value: float
    yen: int = STAKE

    @property
    def label(self) -> str:
        """例 ``6``・``3-5``・``6→10``・``6→10→8``。"""
        joiner = "→" if self.ticket in ORDERED_TICKETS else "-"
        return joiner.join(str(number) for number in self.numbers)

    @property
    def key(self) -> tuple[str, tuple[int, ...]]:
        return self.ticket, self.numbers
