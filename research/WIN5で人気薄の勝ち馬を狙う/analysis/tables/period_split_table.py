"""型ごとの集まり方と「実際 ÷ 市場」が、前半の年と後半の年で同じ向きかを見る表（たまたまかどうかの目安。確かめは次の段）。"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import pandas as pd

from 共通.render import Table

from ..theory.flag_rule import FlagRule
from .cells import ratio


@dataclass(frozen=True)
class PeriodSplitTable:
    """``split_year`` より前と以降に分ける。``longshots`` は人気薄の馬の行。"""

    split_year: int = 2023

    def build(self, longshots: pd.DataFrame, rules: tuple[FlagRule, ...], title: str) -> Table:
        halves = {
            f"〜{self.split_year - 1}年": longshots.loc[longshots["year"] < self.split_year],
            f"{self.split_year}年〜": longshots.loc[longshots["year"] >= self.split_year],
        }
        rows = [[rule.name, *self._row(rule, list(halves.values()))] for rule in rules]
        everything = FlagRule("（人気薄全体）", "", "", lambda x: pd.Series(True, index=x.index))
        rows.append([everything.name, *self._row(everything, list(halves.values()))])
        columns = ["型"] + [f"{name} {item}" for name, item in product(halves, ("勝った", "集まり方", "実際 ÷ 市場"))]
        return Table(columns, rows, title=title)

    def _row(self, rule: FlagRule, halves: list[pd.DataFrame]) -> list[object]:
        return sum((self._cells(rule.flags(half), half) for half in halves), [])

    @staticmethod
    def _cells(flag: pd.Series, half: pd.DataFrame) -> list[object]:
        won = half["finish"] == 1
        hits = int((flag & won).sum())
        lift = ratio(won[flag].mean(), won.mean()) if flag.any() else ""
        return [hits, lift, ratio(hits, half.loc[flag, "market"].sum())]
