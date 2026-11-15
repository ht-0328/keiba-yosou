"""印を付けた全頭の表から、地方の印の買い目の組（買い方 × 馬番の並び）を作る。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 今週の予想.forecast_columns import HORSE_NO, MARK
from 今週の予想.ticket_rules import TicketRule

from .mark_ticket_rules import LOCAL_MARK_RULES


@dataclass(frozen=True)
class MarkPoints:
    """``of(marked)`` は、``marked``（列 ``HORSE_NO``・``MARK``。``MarkRule.assign`` の表）から、``rules`` の組を全部作った
    （買い方, 馬番の並び）の並び。印の付いた馬がいない位置のある買い方は出さない（``TicketRule.combos``）。"""

    rules: tuple[TicketRule, ...] = LOCAL_MARK_RULES

    def of(self, marked: pd.DataFrame) -> list[tuple[TicketRule, tuple[int, ...]]]:
        by_mark: dict[str, list[int]] = {}
        for horse, mark in zip(marked[HORSE_NO], marked[MARK], strict=True):
            by_mark.setdefault(str(mark), []).append(int(horse))
        return [(rule, combo) for rule in self.rules for combo in rule.combos(by_mark, {})]
