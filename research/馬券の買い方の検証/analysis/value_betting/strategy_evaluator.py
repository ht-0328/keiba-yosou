"""1つの戦略を、段階の区切りで評価する。"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from .candidate_picker import CandidatePicker
from .daily_race_cap import DailyRaceCap
from .line_chooser import ValidationLineChooser
from .line_rule import LineRule
from .prepared_window import PreparedWindow
from .protocol import FIXED_LINE, MIN_LINE_POINTS_FULL_YEAR, MIN_LINE_POINTS_HALF_YEAR
from .strategy import Round3Strategy
from .strategy_result import StrategyResult
from .ticket_summary import TicketSummary
from .window_preparer import WindowPreparer


class StrategyEvaluator:
    """戦略1つを、区切りごとに「線を決める → 枠A → （枠B）」の順で当て、テスト期間に買った買い目とまとめを返す。

    - 線: 固定なら 1.25。選ぶなら、直前の1年の対象の馬（馬の選び方で絞ったもの）の枠A で ``ValidationLineChooser`` が決める
      （直前が1年なら 300点以上、半年なら 150点以上）。決まらなければその区切りは買わない。
    - 枠A（``CandidatePicker``）: テスト期間の対象の馬のうち、期待値が線以上の複勝を、レースごとに最大3点。
    - 枠B（``DailyRaceCap``）: レースの選び方が「1日3レースまで」のときだけ。
    テスト期間の結果は、線を決めるのに使わない。
    """

    def __init__(self, preparer: WindowPreparer, picker: CandidatePicker | None = None, cap: DailyRaceCap | None = None) -> None:
        self._preparer = preparer
        self._picker = picker or CandidatePicker()
        self._cap = cap or DailyRaceCap()
        self._chooser = ValidationLineChooser(self._picker)

    def evaluate(self, strategy: Round3Strategy, window_names: Sequence[str]) -> StrategyResult:
        results = {name: self._window(strategy, self._preparer.prepare(name)) for name in window_names}
        frames = [tickets for tickets, _ in results.values() if not tickets.empty]
        tickets = pd.concat(frames, ignore_index=True) if frames else next(iter(results.values()))[0]
        return StrategyResult(
            strategy, by_window={name: TicketSummary.of(tickets) for name, (tickets, _) in results.items()},
            lines={name: line for name, (_, line) in results.items()}, total=TicketSummary.of(tickets), tickets=tickets,
        )

    def _window(self, strategy: Round3Strategy, prepared: PreparedWindow) -> tuple[pd.DataFrame, float]:
        """（その区切りのテスト期間に買った買い目, 使った線）。"""
        line = self._line(strategy, prepared)
        tickets = self._picker.pick(prepared.test[strategy.selection.rows_of(prepared.test)], line)
        if strategy.race_rule.caps_per_day:
            tickets = self._cap.apply(tickets, prepared.races)
        return tickets, line

    def _line(self, strategy: Round3Strategy, prepared: PreparedWindow) -> float:
        if strategy.line_rule is LineRule.FIXED:
            return FIXED_LINE
        min_points = MIN_LINE_POINTS_FULL_YEAR if prepared.history_is_full_year else MIN_LINE_POINTS_HALF_YEAR
        return self._chooser.choose(prepared.history[strategy.selection.rows_of(prepared.history)], min_points)
