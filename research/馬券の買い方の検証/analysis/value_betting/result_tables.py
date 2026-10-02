"""探索・確認・最後の1回の結果を、人が読む表にする。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np

from 共通.render import Table

from .operational_summary import OperationalSummary
from .strategy_result import StrategyResult
from .ticket_summary import TicketSummary


def rate_text(value: float) -> str:
    """回収率の見た目（``96.4%``）。無ければ空。"""
    return "" if value is None or np.isnan(value) else f"{value * 100:.1f}%"


def line_text(value: float) -> str:
    """線の見た目（``1.25``）。決まらなければ「買わない」。"""
    return "買わない" if value is None or np.isnan(value) else f"{value:.2f}"


class ResultTables:
    """戦略ごとの結果（``StrategyResult``）と目安（``TicketSummary``）から表を作る。採否の文字は呼ぶ側が渡す。"""

    def baseline_table(self, summaries: Mapping[str, TicketSummary], title: str) -> Table:
        rows = [[name, *self._summary_cells(summary)] for name, summary in summaries.items()]
        return Table(["目安", *self._SUMMARY_COLUMNS], rows, title=title, note="1点 100円の均等、全レース。期待値や線は使わない。")

    def results_table(self, results: Sequence[StrategyResult], verdicts: Sequence[str], title: str) -> Table:
        window_names = list(results[0].by_window) if results else []
        columns = ["番号", "戦略", *self._SUMMARY_COLUMNS, *[f"{name} の回収率" for name in window_names], "採否"]
        rows = [[number, result.strategy.name, *self._summary_cells(result.total),
                 *[rate_text(result.by_window[name].rate) for name in window_names], verdict]
                for number, (result, verdict) in enumerate(zip(results, verdicts), start=1)]
        return Table(columns, rows, title=title,
                     note="回収率 = 払戻 ÷ 賭け金。90% の幅は開催日単位のブートストラップ、控えめな見積もりは 回収率 − 1.645 × 開催日単位のばらつき。"
                          "すべて確定オッズでの検証。")

    def lines_table(self, results: Sequence[StrategyResult], title: str) -> Table:
        window_names = list(results[0].lines) if results else []
        rows = [[number, result.strategy.name, *[line_text(result.lines[name]) for name in window_names]]
                for number, result in enumerate(results, start=1)]
        return Table(["番号", "戦略", *window_names], rows, title=title,
                     note="線は区切りごとに直前の1年で決めた（固定の戦略は 1.25）。「買わない」は条件に合う線が無かった区切り。")

    def window_table(self, result: StrategyResult, title: str) -> Table:
        rows = [[name, line_text(result.lines[name]), *self._summary_cells(summary)] for name, summary in result.by_window.items()]
        rows.append(["合計", "", *self._summary_cells(result.total)])
        return Table(["区切り", "線", *self._SUMMARY_COLUMNS], rows, title=title)

    def operational_table(self, summary: OperationalSummary, title: str) -> Table:
        rows = [
            ["買った開催日数", summary.days], ["買ったレース数", summary.races], ["うち平地の重賞", summary.graded_races],
            ["点数", summary.points], ["1開催日のレース数（平均）", self._number(summary.races_per_day_mean)],
            ["1開催日のレース数（最大）", summary.races_per_day_max], ["1レースの点数（平均）", self._number(summary.points_per_race_mean)],
            ["1レースの賭け金（円。1点 100円のとき。平均）", self._number(summary.yen_per_race_mean)],
            ["1開催日の賭け金（円。平均）", self._number(summary.yen_per_day_mean)], ["1か月の賭け金（円。平均）", self._number(summary.yen_per_month_mean)],
        ]
        return Table(["項目", "値"], rows, title=title, note="複勝だけ。1点 100円の均等。金額を変えるときは、この表の値に倍率を掛ける。")

    _SUMMARY_COLUMNS: tuple[str, ...] = (
        "点数", "レース数", "開催日数", "賭け金（円）", "払戻（円）", "的中率", "回収率", "90%の下限", "90%の上限", "控えめな見積もり",
    )

    def _summary_cells(self, summary: TicketSummary) -> list[object]:
        return [summary.points, summary.races, summary.days, summary.stake_yen, summary.payout_yen, rate_text(summary.hit_rate),
                rate_text(summary.rate), rate_text(summary.lower), rate_text(summary.upper), rate_text(summary.conservative)]

    def _number(self, value: float) -> str:
        return "" if value is None or np.isnan(value) else f"{value:.1f}"
