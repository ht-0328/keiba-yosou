"""終わったレースの印の買い目に、確定オッズの板で1点ごとの期待値を付ける。"""

from __future__ import annotations

import sys

import duckdb
import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.repository import FinalOddsRepository, RaceDayRange

from 今週の予想.mark_ticket_values import MarkTicketValues
from 今週の予想.mark_tickets import RULE
from 今週の予想.ticket_rules import MARK_VALUE_LABELS


class MarkValueTickets:
    """買い目（``MarkTickets`` などの1行 = 1点）のうち、全レースで出す印の買い目（``MARK_VALUE_LABELS``）の期待値を、
    開催日を月ごとに区切って、その月の確定オッズの板（``FinalOddsRepository``）で付ける（``MarkTicketValues``。今週の予想と同じ部品）。
    3連単の板は1レース数千行あるので、全期間を一度に読まずに月ごとに読む。"""

    def __init__(self, con: duckdb.DuckDBPyConnection, values: MarkTicketValues) -> None:
        self._con = con
        self._values = values

    def attach(self, tickets: pd.DataFrame, marked: pd.DataFrame) -> pd.DataFrame:
        needed = self._values.needed()
        mine = tickets[RULE].isin(MARK_VALUE_LABELS)
        if not mine.any() or marked.empty:
            return tickets
        table = marked.assign(race_id=marked["race_id"].astype(str))
        months = pd.to_datetime(table["race_date"]).dt.to_period("M")
        parts = [tickets[~mine]]
        ours = tickets[mine].assign(race_id=tickets.loc[mine, "race_id"].astype(str))
        for _, group in table.groupby(months, sort=True):
            dates = pd.to_datetime(group["race_date"])
            races = set(group["race_id"])
            boards = {ticket_type: self._board(ticket_type, RaceDayRange(dates.min().date(), dates.max().date()), races) for ticket_type in needed}
            print(f"印の買い目の期待値: {dates.min():%Y-%m}", file=sys.stderr, flush=True)
            parts.append(self._values.attach(ours[ours["race_id"].isin(races)], group, boards))
        return pd.concat(parts).sort_index()

    def _board(self, ticket_type: TicketType, days: RaceDayRange, races: set[str]) -> pd.DataFrame:
        board = FinalOddsRepository(self._con, ticket_type).read(days)
        board = board[board["race_id"].astype(str).isin(races)]
        return pd.DataFrame({"race_id": board["race_id"].astype(str), "combo": board["combo"].astype(str), "odds": board["odds"].astype(float)})
