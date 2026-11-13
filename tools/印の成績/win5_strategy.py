"""WIN5 の買い方（並べ方・予算・買う日の線）の1つ。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.form_aptitude_win5_tickets.formation import LegOrdering


@dataclass(frozen=True)
class Win5Strategy:
    """設計書「近走と適性からWIN5の買い目を決める」16 の 4. の 40 通りの1つ。"""

    ordering: LegOrdering
    budget: int
    line: float

    @property
    def label(self) -> str:
        """``上乗せの順・100点・線1.25`` の形（表の「買い方」の列）。"""
        return f"{self.ordering.label}・{self.budget}点・線{self.line:.2f}"
