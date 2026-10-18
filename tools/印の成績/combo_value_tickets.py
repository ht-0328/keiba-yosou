"""終わったレースの印と確定オッズの板から、組の期待値で選ぶ買い目を作る。"""

from __future__ import annotations

import sys

import duckdb
import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.repository import FinalOddsRepository, RaceDayRange

from 今週の予想.combo_value_picker import ComboValuePicker
from 今週の予想.mark_tickets import COLUMNS


class ComboValueTickets:
    """印を付けた表（``BacktestMarker.mark``）の開催日を月ごとに区切り、その月の確定オッズの板（``FinalOddsRepository``。
    ルールの券種と3連単）を読んで、``ComboValuePicker`` で買い目（1行 = 1点。列は ``MarkTickets`` の ``COLUMNS``）を作る。

    3連単の板は1レース数千行あるので、全期間を一度に読まずに月ごとに読む。重みの無い券種（``combo_blend.json`` が無い）は 0点。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, picker: ComboValuePicker) -> None:
        self._con = con
        self._picker = picker

    def build(self, marked: pd.DataFrame) -> pd.DataFrame:
        needed = self._picker.needed()
        if not needed or marked.empty:
            return pd.DataFrame(columns=list(COLUMNS))
        table = marked.assign(race_id=marked["race_id"].astype(str))
        months = pd.to_datetime(table["race_date"]).dt.to_period("M")
        parts = [self._month(group, needed) for _, group in table.groupby(months, sort=True)]
        return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=list(COLUMNS))

    def _month(self, marked: pd.DataFrame, needed: tuple[TicketType, ...]) -> pd.DataFrame:
        dates = pd.to_datetime(marked["race_date"])
        days = RaceDayRange(dates.min().date(), dates.max().date())
        races = set(marked["race_id"])
        boards = {ticket_type: self._board(ticket_type, days, races) for ticket_type in needed}
        print(f"組の期待値の買い目: {dates.min():%Y-%m}", file=sys.stderr, flush=True)
        return self._picker.pick(marked, boards)

    def _board(self, ticket_type: TicketType, days: RaceDayRange, races: set[str]) -> pd.DataFrame:
        board = FinalOddsRepository(self._con, ticket_type).read(days)
        board = board[board["race_id"].astype(str).isin(races)]
        return pd.DataFrame({"race_id": board["race_id"].astype(str), "combo": board["combo"].astype(str), "odds": board["odds"].astype(float)})
