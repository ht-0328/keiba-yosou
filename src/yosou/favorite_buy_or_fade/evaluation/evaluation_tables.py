"""1年ごとの評価の結果を、表にする。"""

from __future__ import annotations

import pandas as pd

from 共通.render import Table

from ..decision import BET_KINDS, DECISION
from ..similarity import UNIT
from .decision_summary import COLUMNS, DecisionSummary
from .kind_summary import KIND_COLUMNS, KindSummary
from .stake_plan import StakePlan

#: 全部の行をまとめた行の見出し。
_TOTAL = "全体"


class EvaluationTables:
    """判定した1番人気の表（``YearlyEvaluation`` の結果）から、年ごと・判定ごと・単位ごとの表を作る（設計書 16）。

    ``year_column`` は評価の年の列の名前。
    """

    def __init__(self, plan: StakePlan, year_column: str) -> None:
        self._summary = DecisionSummary(plan)
        self._kinds = KindSummary()
        self._plan = plan
        self._year = year_column

    def tables(self, rows: pd.DataFrame) -> list[Table]:
        return [self.by_year(rows), self.by_kind(rows), self.by_unit(rows)]

    def by_year(self, rows: pd.DataFrame) -> Table:
        """年ごとのまとめ（最後に全部の年を合わせた行）。"""
        return self._grouped(rows, self._year, "年ごとの結果", self._stake_note())

    def by_unit(self, rows: pd.DataFrame) -> Table:
        """単位ごとのまとめ（全部の年を合わせる）。"""
        return self._grouped(rows, UNIT, "単位ごとの結果（全部の年）", "単位は、評価の年ごとに学習データの頭数で決め直す。")

    def by_kind(self, rows: pd.DataFrame) -> Table:
        """判定ごとの成績（全部の年を合わせる）。"""
        records = [self._kinds.summarize(kind, rows[rows[DECISION] == kind]) for kind in BET_KINDS]
        return Table(list(KIND_COLUMNS), [*records, self._kinds.summarize(_TOTAL, rows)],
                     title="判定ごとの成績（全部の年）",
                     note="回収率は、どの判定の馬も単勝・複勝を 100円ずつ買ったとみなしたもの（判定が着順を分けられているかを見る）。")

    def _grouped(self, rows: pd.DataFrame, key: str, title: str, note: str) -> Table:
        records = [[str(value), *self._summary.summarize(part).values()] for value, part in rows.groupby(key, sort=True)]
        total = [_TOTAL, *self._summary.summarize(rows).values()]
        return Table([key, *COLUMNS], [*records, total], title=title, note=note)

    def _stake_note(self) -> str:
        plan = self._plan
        return (f"掛け金は1頭あたり「単勝と複勝」= 単勝 {plan.win_and_place_win}円・複勝 {plan.win_and_place_place}円、"
                f"「複勝だけ」= 複勝 {plan.place_only_place}円、「消す」= 買わない。"
                "「全部を〜で買った」は、同じ年の1番人気を全部その買い方で買ったときの回収率。")
