"""終わったレースの印と確定オッズの板・枠番から、枠連の組の期待値で選ぶ買い目を作る。"""

from __future__ import annotations

import sys

import duckdb
import pandas as pd

from yosou.shared.betting import BRACKET, TicketType
from yosou.shared.combo_value import BracketBlendWeights
from yosou.shared.repository import FinalOddsRepository, FrameRepository, RaceDayRange

from 今週の予想.bracket_value_picker import BracketValuePicker
from 今週の予想.mark_tickets import COLUMNS
from 今週の予想.ticket_rules import BRACKET_VALUE_RULE


class BracketValueTickets:
    """印を付けた表（``BacktestMarker.mark``）の開催日を月ごとに区切り、その月の確定オッズの板（馬連・3連単・枠連）と枠番を読んで、
    ``BracketValuePicker`` で枠連の組の期待値の買い目（1行 = 1点。列は ``MarkTickets`` の ``COLUMNS``）を作る。

    重みは ``weights``（モデルの置き場所の ``bracket_blend.json``）。``fold_weights``（区切り → 重み）を渡すと、区切りごとにその重みで選ぶ
    （研究「レースの種類ごとの買い方」の、区切りごとに直前1年で推定した重み）。重みが無ければ 0点。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, weights: BracketBlendWeights | None,
                 fold_weights: dict[str, BracketBlendWeights] | None = None) -> None:
        self._con = con
        self._weights = weights
        self._fold_weights = fold_weights or {}

    def build(self, marked: pd.DataFrame) -> pd.DataFrame:
        if marked.empty or (self._weights is None and not self._fold_weights):
            return pd.DataFrame(columns=list(COLUMNS))
        table = marked.assign(race_id=marked["race_id"].astype(str))
        months = pd.to_datetime(table["race_date"]).dt.to_period("M")
        parts = [self._month(group) for _, group in table.groupby(months, sort=True)]
        parts = [part for part in parts if not part.empty]
        return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=list(COLUMNS))

    def _month(self, marked: pd.DataFrame) -> pd.DataFrame:
        dates = pd.to_datetime(marked["race_date"])
        days = RaceDayRange(dates.min().date(), dates.max().date())
        races = set(marked["race_id"])
        boards = {ticket_type: self._board(ticket_type, days, races) for ticket_type in (TicketType.QUINELLA, TicketType.TRIFECTA)}
        bracket = self._board(BRACKET, days, races)
        frames = FrameRepository(self._con).read(days)
        frames = frames[frames["race_id"].astype(str).isin(races)]
        print(f"枠連の組の期待値の買い目: {dates.min():%Y-%m}", file=sys.stderr, flush=True)
        parts = [BracketValuePicker(BRACKET_VALUE_RULE, self._fold_weights.get(str(fold), self._weights)).pick(rows, boards, bracket, frames)
                 for fold, rows in marked.groupby("fold", sort=False)]
        parts = [part for part in parts if not part.empty]
        return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=list(COLUMNS))

    def _board(self, ticket_type, days: RaceDayRange, races: set[str]) -> pd.DataFrame:
        board = FinalOddsRepository(self._con, ticket_type).read(days)
        board = board[board["race_id"].astype(str).isin(races)]
        return pd.DataFrame({"race_id": board["race_id"].astype(str), "combo": board["combo"].astype(str), "odds": board["odds"].astype(float)})
