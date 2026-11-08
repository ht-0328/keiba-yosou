"""人気薄の馬について、手がかり（または型）ごとに、勝った馬の中の割合と人気薄全体の中の割合・市場の見立てとの比を並べる表。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from ..theory.flag_rule import FlagRule
from .cells import percent, ratio

_NOTE = ("勝った馬の中の割合が人気薄全体の中の割合より大きいほど、その手がかりは勝ち馬に集まっている（集まり方 = 当てはまる馬の勝率 ÷ 人気薄全体の勝率）。"
         "実際 ÷ 市場 は、当てはまる馬が勝った数 ÷ その馬たちのオッズから見た勝率の合計。全体の値より大きければ、市場がその手がかりを見落としている。")


@dataclass(frozen=True)
class FlagShareTable:
    """``longshots`` は人気薄の馬の行（``finish``・``market`` の列が要る）。``extra`` は型の表で足す「どれも無し」のような列の名前。"""

    def build(self, longshots: pd.DataFrame, rules: tuple[FlagRule, ...], title: str, extra: tuple[str, ...] = ()) -> Table:
        won = longshots["finish"] == 1
        base_rate = won.mean()
        flags = {rule.name: (rule.group, rule.flags(longshots)) for rule in rules}
        flags.update({name: ("", longshots[name].astype(bool)) for name in extra})
        rows = [self._row(name, group, flag, won, base_rate, longshots["market"]) for name, (group, flag) in flags.items()]
        rows.append(["（人気薄全体）", "", len(longshots), int(won.sum()), "100.0%", "100.0%", "1.00", ratio(won.sum(), longshots["market"].sum())])
        columns = ["手がかり", "まとまり", "当てはまる頭数", "勝った", "勝った馬の中の割合", "人気薄全体の中の割合", "集まり方", "実際 ÷ 市場"]
        return Table(columns, rows, title=title, note=_NOTE)

    @staticmethod
    def _row(name: str, group: str, flag: pd.Series, won: pd.Series, base_rate: float, market: pd.Series) -> list[object]:
        hits = int((flag & won).sum())
        lift = (won[flag].mean() / base_rate) if flag.any() and base_rate else float("nan")
        return [name, group, int(flag.sum()), hits, percent(hits, won.sum()), percent(flag.sum(), len(flag)),
                f"{lift:.2f}" if flag.any() else "", ratio(hits, market[flag].sum())]
