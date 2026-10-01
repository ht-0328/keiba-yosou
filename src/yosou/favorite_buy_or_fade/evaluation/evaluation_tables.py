"""1年ごとの評価の結果を、表にする。"""

from __future__ import annotations

import pandas as pd

from 共通.render import Table

from ..decision import BET_KINDS, DECISION
from ..similarity import UNIT
from .decision_summary import COLUMNS, DecisionSummary
from .evaluation_periods import EvaluationPeriods
from .kind_summary import KIND_COLUMNS, KindSummary
from .stake_plan import StakePlan

#: 全部の行をまとめた行の見出し。
_TOTAL = "全体"


class EvaluationTables:
    """判定した1番人気の表（``YearlyEvaluation`` の結果）から、年ごと・判定ごと・単位ごとの表を作る（設計書 16）。

    ``year_column`` は評価の年の列の名前。年ごとの表には、方針を決める年と確かめる年のまとめの行を足し、
    判定ごと・単位ごとの表は、方針を決める年と確かめる年で別の表にする（``EvaluationPeriods``）。
    """

    def __init__(self, plan: StakePlan, year_column: str, periods: EvaluationPeriods) -> None:
        self._summary = DecisionSummary(plan)
        self._kinds = KindSummary()
        self._plan = plan
        self._year = year_column
        self._periods = periods

    def tables(self, rows: pd.DataFrame) -> list[Table]:
        parts = self._periods.split(rows)
        return [self.by_year(rows),
                *[self.by_kind(part, name) for name, part in parts.items()],
                *[self.by_unit(part, name) for name, part in parts.items()]]

    def by_year(self, rows: pd.DataFrame) -> Table:
        """年ごとのまとめ。そのあとに、方針を決める年・確かめる年・全部の年を合わせた行。"""
        records = [[str(year), *self._summary.summarize(part).values()]
                   for year, part in rows.groupby(self._year, sort=True)]
        periods = [[name, *self._summary.summarize(part).values()] for name, part in self._periods.split(rows).items()]
        total = [_TOTAL, *self._summary.summarize(rows).values()]
        return Table([self._year, *COLUMNS], [*records, *periods, total], title="年ごとの結果", note=self._year_note())

    def by_unit(self, rows: pd.DataFrame, period: str) -> Table:
        """単位ごとのまとめ（``period`` の年を合わせる）。"""
        records = [[str(unit), *self._summary.summarize(part).values()] for unit, part in rows.groupby(UNIT, sort=True)]
        total = [_TOTAL, *self._summary.summarize(rows).values()]
        return Table([UNIT, *COLUMNS], [*records, total], title=f"単位ごとの結果（{period}）",
                     note="単位は、評価の年ごとに学習データの頭数で決め直す。")

    def by_kind(self, rows: pd.DataFrame, period: str) -> Table:
        """判定ごとの成績（``period`` の年を合わせる）。"""
        records = [self._kinds.summarize(kind, rows[rows[DECISION] == kind]) for kind in BET_KINDS]
        return Table(list(KIND_COLUMNS), [*records, self._kinds.summarize(_TOTAL, rows)],
                     title=f"判定ごとの成績（{period}）",
                     note="回収率は、どの判定の馬も単勝・複勝を 100円ずつ買ったとみなしたもの（判定が着順を分けられているかを見る）。")

    def _year_note(self) -> str:
        plan = self._plan
        return (f"掛け金は1頭あたり「単勝と複勝」= 単勝 {plan.win_and_place_win}円・複勝 {plan.win_and_place_place}円、"
                f"「複勝だけ」= 複勝 {plan.place_only_place}円、「消す」= 買わない。"
                "「全部を〜で買った」は、同じ年の1番人気を全部その買い方で買ったときの回収率。"
                "方針（線・k・重みなど）を比べて選ぶときは、方針を決める年の行だけを見る。確かめる年の行は、選んだ方針のまま確かめるためのもの。")
