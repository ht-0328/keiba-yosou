"""探索期間の 40 通りの成績と、予算ごとのいちばん良い買い方の表。"""

from __future__ import annotations

import pandas as pd

from 共通.render import Table

from yosou.form_aptitude_win5_tickets.formation import BUDGETS
from yosou.form_aptitude_win5_tickets.payout import TICKET_YEN
from yosou.form_aptitude_win5_tickets.settlement import STRATEGY

from 印の成績.win5_day_bets import STRATEGIES
from 印の成績.win5_strategy_choice import MIN_DAYS, Win5StrategyChoice
from 印の成績.win5_strategy_summary import DAYS, RECOVERY
from 印の成績.win5_summary_cells import HEADERS, Win5SummaryCells

#: 選んだ買い方・候補に残らなかった買い方の印。
CHOSEN_MARK = "選んだ"
TOO_FEW_MARK = f"{MIN_DAYS}日未満"


class Win5SelectionReport:
    """設計書「近走と適性からWIN5の買い目を決める」16 の 4.。探索期間の 40 通りの成績（回収率の高い順。選んだ買い方と、買った日が
    30日未満で候補に残らなかった買い方に印）と、予算ごとに並べ方と線の組み合わせのうちいちばん良かったものの成績（利用者が予算を
    決め直すための表）。"""

    def __init__(self) -> None:
        self._cells = Win5SummaryCells()
        self._choice = Win5StrategyChoice()

    def tables(self, summary: pd.DataFrame, chosen: str | None) -> list[Table]:
        """``summary`` は探索期間の、この予想の 40 通りの成績（``Win5StrategySummary``）。``chosen`` は決まりで選んだ買い方（無ければ None）。"""
        return [self._all(summary, chosen), self._by_budget(summary)]

    def _all(self, summary: pd.DataFrame, chosen: str | None) -> Table:
        by_label = summary.set_index(STRATEGY)
        rows = []
        for strategy in STRATEGIES:
            row = by_label.loc[strategy.label] if strategy.label in by_label.index else None
            rows.append([strategy.label, *self._cells.cells(row), self._mark(strategy.label, row, chosen)])
        rows.sort(key=lambda cells: self._sort_key(by_label, cells[0]))
        note = ("決まり: 買った日が 30日以上の買い方のうち、回収率（同じなら的中率）がいちばん高いものを選ぶ。回収率が 100% を超えるものが"
                "無ければ「選べる買い方なし」（設計書 16 の 4.）。")
        return Table(["買い方", *HEADERS, "印"], rows, title="WIN5 の探索期間の 40 通り（並べ方 × 予算 × 線）", note=note)

    def _by_budget(self, summary: pd.DataFrame) -> Table:
        rows = []
        for budget in BUDGETS:
            labels = [strategy.label for strategy in STRATEGIES if strategy.budget == budget]
            best = self._choice.best(summary.loc[summary[STRATEGY].isin(labels)])
            row = summary.loc[summary[STRATEGY] == best].iloc[0] if best is not None else None
            rows.append([budget, budget * TICKET_YEN, best or "（30日以上の買い方なし）", *self._cells.cells(row)])
        return Table(["予算（点）", "1回の金額（円）", "いちばん良い買い方", *HEADERS], rows,
                     title="WIN5 の予算ごとのいちばん良い買い方（探索期間）",
                     note="予算ごとに、並べ方と線の組み合わせのうち探索期間で同じ決まりでいちばん良かったもの。予算を決め直すときの材料。")

    def _mark(self, label: str, row: pd.Series | None, chosen: str | None) -> str:
        if label == chosen:
            return CHOSEN_MARK
        if row is None or int(row[DAYS]) < MIN_DAYS:
            return TOO_FEW_MARK
        return ""

    def _sort_key(self, by_label: pd.DataFrame, label: str) -> tuple[float, str]:
        """回収率の高い順（買った日の無い買い方は最後）。"""
        if label not in by_label.index or pd.isna(by_label.loc[label, RECOVERY]):
            return (float("inf"), label)
        return (-float(by_label.loc[label, RECOVERY]), label)
