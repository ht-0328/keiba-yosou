"""印を付けた全頭の表から、地方の印の買い目の組（買い方 × 馬番の並び）を作る。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 今週の予想.forecast_columns import HORSE_NO, MARK, PLACE_VALUE
from 今週の予想.mark_rule import VALUE_MARK
from 今週の予想.ticket_rules import PLACE_VALUE_LINE, TicketRule

from .mark_ticket_rules import LOCAL_MARK_RULES


@dataclass(frozen=True)
class MarkPoints:
    """``of(marked)`` は、``marked``（列 ``HORSE_NO``・``MARK``・``PLACE_VALUE``。``MarkRule.assign`` の表）から、``rules`` の組を全部作った
    （買い方, 馬番の並び）の並び。☆ は複勝の期待値が ``PLACE_VALUE_LINE`` 以上の馬だけを相手に入れる（線に届かない ☆ は表示だけ。
    中央の印の買い目と、研究で数えた道具「印の成績」の組と同じ）。印の付いた馬がいない位置のある買い方は出さない（``TicketRule.combos``）。"""

    rules: tuple[TicketRule, ...] = LOCAL_MARK_RULES

    def of(self, marked: pd.DataFrame) -> list[tuple[TicketRule, tuple[int, ...]]]:
        shown_only = (marked[MARK] == VALUE_MARK) & ~(marked[PLACE_VALUE] >= PLACE_VALUE_LINE)
        by_mark: dict[str, list[int]] = {}
        for horse, mark in zip(marked.loc[~shown_only, HORSE_NO], marked.loc[~shown_only, MARK], strict=True):
            by_mark.setdefault(str(mark), []).append(int(horse))
        return [(rule, combo) for rule in self.rules for combo in rule.combos(by_mark, {})]
