"""戦略の結果の表。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from 共通.render import Table

from ..participation import RacePattern
from ..search.adoption_rule import AdoptionRule
from ..search.strategy import Strategy
from ..search.strategy_result import StrategyResult
from ..settlement import SettlementTable
from ..ticket import BASELINE_PLANS
from .plan_summary_tables import rate_text
from .return_summary import ReturnSummary

#: 基準として並べる買い方（全レースで買ったとき）。基準の2つと、本命の複勝。
BASELINE_NAMES: tuple[str, ...] = (*(plan.name for plan in BASELINE_PLANS), "本命複勝")
_RESULT_COLUMNS: tuple[str, ...] = (
    "番号", "参加パターン", "荒れ度の線", "本命の線", "危険の線", "週の上位", "広めの買い方", "少点数の買い方",
    "対象レース", "買ったレース", "点数", "賭け金（円）", "払戻（円）", "回収率", "的中レース率", "最大を除く回収率", "採否",
)


class StrategyTables:
    """探索・確認の結果を、人が読む表にする（戦略ごとの回収率、採用候補の月別、基準の買い方）。"""

    def __init__(self, patterns: Mapping[str, RacePattern], rule: AdoptionRule) -> None:
        self._patterns = dict(patterns)
        self._rule = rule

    def results_table(self, results: Sequence[StrategyResult], *, title: str, limit: int | None = None) -> Table:
        shown = list(results)[:limit] if limit else list(results)
        rows = [self._result_row(index, result) for index, result in enumerate(shown, start=1)]
        note = f"全 {len(results)} 戦略のうち {len(shown)} 行。採否の基準: {self._rule.describe()}"
        return Table(list(_RESULT_COLUMNS), rows, title=title, note=note)

    def monthly_table(self, results: Sequence[StrategyResult], *, title: str) -> Table:
        months = sorted({month for result in results for month in result.by_month})
        rows = [[index, self._describe(result.strategy), *(self._month_cell(result, month) for month in months)]
                for index, result in enumerate(results, start=1)]
        return Table(["番号", "戦略", *months], rows, title=title, note="月ごとの回収率（買ったレースが無い月は空）")

    def baseline_table(self, settlement: SettlementTable, race_ids: Sequence[str], *, title: str) -> Table:
        rows = []
        for name in BASELINE_NAMES:
            plan_rows = settlement.for_plan(name)
            summary = ReturnSummary.from_rows(plan_rows[plan_rows.index.isin(race_ids)])
            rows.append([name, summary.races, summary.bet_races, summary.points, summary.stake_yen, summary.payout_yen,
                         rate_text(summary.return_rate), rate_text(summary.hit_race_rate)])
        return Table(["買い方（全レース）", "対象レース", "買ったレース", "点数", "賭け金（円）", "払戻（円）", "回収率", "的中レース率"],
                     rows, title=title)

    def _result_row(self, index: int, result: StrategyResult) -> list[object]:
        strategy, total = result.strategy, result.total
        return [
            index, self._patterns[strategy.pattern_key].label, self._upset_text(strategy),
            self._number(strategy.form_threshold), self._number(strategy.danger_threshold),
            strategy.top_k if strategy.top_k is not None else "", strategy.wide_plan or "", strategy.narrow_plan or "",
            result.race_count, total.bet_races, total.points, total.stake_yen, total.payout_yen,
            rate_text(total.return_rate), rate_text(total.hit_race_rate), rate_text(total.return_rate_without_max),
            self._rule.verdict(total, result.monthly_rates),
        ]

    def _describe(self, strategy: Strategy) -> str:
        pattern = self._patterns[strategy.pattern_key].label
        parts = [pattern, self._upset_text(strategy),
                 f"本命 {strategy.form_threshold:.2f}" if strategy.form_threshold is not None else "",
                 f"危険 {strategy.danger_threshold:.2f}" if strategy.danger_threshold is not None else "",
                 f"上位 {strategy.top_k}" if strategy.top_k is not None else "",
                 strategy.wide_plan or "", strategy.narrow_plan or ""]
        return " / ".join(part for part in parts if part)

    def _upset_text(self, strategy: Strategy) -> str:
        if strategy.upset_share is None:
            return ""
        return f"上位{strategy.upset_share:.0%}（{strategy.upset_threshold:.3f}）"

    def _number(self, value: float | None) -> str:
        return "" if value is None else f"{value:.2f}"

    def _month_cell(self, result: StrategyResult, month: str) -> str:
        summary = result.by_month.get(month)
        return rate_text(summary.return_rate) if summary else ""
