"""買い方ごとの要約の表。"""

from __future__ import annotations

from 共通.perf import percent
from 共通.render import Table

from ..settlement import SettlementTable
from ..settlement.settlement_table import PLAN, POINTS, SKIPPED
from .return_summary import ReturnSummary

#: 表の見出し。
_COLUMNS: tuple[str, ...] = (
    "買い方", "レース数", "買ったレース", "点数", "賭け金（円）", "払戻（円）", "回収率", "的中レース率", "最大を除く回収率",
)


class PlanSummaryTables:
    """精算表から、買い方ごとの回収率の表と、見送りの理由の内訳の表を作る（``--settle-only`` の出力）。"""

    def __init__(self, settlement: SettlementTable) -> None:
        self._settlement = settlement

    def tables(self) -> list[Table]:
        return [self._returns(), self._skips()]

    def _returns(self) -> Table:
        rows = [self._row(name, ReturnSummary.from_rows(self._settlement.rows[self._settlement.rows[PLAN] == name]))
                for name in self._settlement.plan_names]
        return Table(list(_COLUMNS), rows, title="買い方ごとの回収率（全レースで買ったとき）", note="回収率 = 払戻 ÷ 賭け金（1点100円）")

    def _row(self, name: str, summary: ReturnSummary) -> list[object]:
        return [
            name, summary.races, summary.bet_races, summary.points, summary.stake_yen, summary.payout_yen,
            rate_text(summary.return_rate), rate_text(summary.hit_race_rate), rate_text(summary.return_rate_without_max),
        ]

    def _skips(self) -> Table:
        skipped = self._settlement.rows[self._settlement.rows[POINTS] == 0]
        counts = skipped.groupby([PLAN, SKIPPED]).size().reset_index(name="レース数")
        rows = [[plan, reason, int(count)] for plan, reason, count in counts.itertuples(index=False)]
        return Table(["買い方", "見送りの理由", "レース数"], rows, title="見送りの内訳")


def rate_text(value: float | None) -> str:
    """率の見た目（``86.4%``）。無ければ空。"""
    return "" if value is None else percent(value)
