"""組の期待値と枠連の、印と消に依らない候補の組を1回だけ作り、印を付けた表ごとに買い目を選ぶ。"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import duckdb
import pandas as pd

from yosou.shared.betting import BRACKET, TicketType
from yosou.shared.repository import BracketBlendWeightsRepository, ComboBlendWeightsRepository, FinalOddsRepository, FrameRepository, RaceDayRange

from 今週の予想.bracket_value_picker import BracketValuePicker
from 今週の予想.combo_value_picker import ComboValuePicker
from 今週の予想.mark_tickets import COLUMNS
from 今週の予想.ticket_rules import BRACKET_VALUE_RULE, COMBO_VALUE_RULES

from .search_inputs import SearchInputs


class ComboCandidates:
    """道具「印の成績」の ``ComboValueTickets``・``BracketValueTickets`` と同じ買い目を、2段に分けて作る。

    ``build`` は印と消に依らない段: 開催日を月ごとに区切って確定オッズの板と枠番を読み、``ComboValuePicker.candidates``・
    ``BracketValuePicker.candidates``（組の期待値が線以上でオッズが上限以下の組）を全期間ぶん覚える。
    ``tickets`` は印と消で決まる段: 印を付けた表から ``select`` で買い目（``MarkTickets`` の ``COLUMNS``）を選ぶ。
    重みは ``models`` の ``combo_blend.json``・``bracket_blend.json``（印の成績の既定と同じく、全部の区切りに同じ重み）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, inputs: SearchInputs, models: Path) -> None:
        self._con = con
        self._inputs = inputs
        self._picker = ComboValuePicker(COMBO_VALUE_RULES, ComboBlendWeightsRepository(models).load())
        self._bracket = BracketValuePicker(BRACKET_VALUE_RULE, BracketBlendWeightsRepository(models).load())
        self._candidates: list[pd.DataFrame] = []
        self._bracket_candidates: pd.DataFrame = pd.DataFrame()
        self._frames: pd.DataFrame = pd.DataFrame()

    def build(self) -> None:
        started = time.monotonic()
        horses = self._inputs.horses()
        horses = horses.assign(race_id=horses["race_id"].astype(str))
        months = pd.to_datetime(horses["race_date"]).dt.to_period("M")
        needed = tuple(dict.fromkeys([*self._picker.needed(), TicketType.QUINELLA, TicketType.TRIFECTA]))
        parts: list[list[pd.DataFrame]] = [[] for _ in self._picker.rules]
        bracket_parts, frame_parts = [], []
        for month, group in horses.groupby(months, sort=True):
            dates = pd.to_datetime(group["race_date"])
            days = RaceDayRange(dates.min().date(), dates.max().date())
            races = set(group["race_id"])
            boards = {ticket_type: self._board(ticket_type, days, races) for ticket_type in needed}
            for index, candidate in enumerate(self._picker.candidates(group, boards)):
                if not candidate.empty:
                    parts[index].append(candidate)
            frames = FrameRepository(self._con).read(days)
            frames = frames[frames["race_id"].astype(str).isin(races)]
            bracket = self._bracket.candidates(group, boards, self._board(BRACKET, days, races), frames)
            if not bracket.empty:
                bracket_parts.append(bracket)
            frame_parts.append(frames)
            print(f"  組の期待値の候補: {month}（{time.monotonic() - started:.0f}秒）", file=sys.stderr, flush=True)
        self._candidates = [pd.concat(part, ignore_index=True) if part else pd.DataFrame() for part in parts]
        self._bracket_candidates = pd.concat(bracket_parts, ignore_index=True) if bracket_parts else pd.DataFrame()
        self._frames = pd.concat(frame_parts, ignore_index=True) if frame_parts else pd.DataFrame()

    def tickets(self, marked: pd.DataFrame) -> pd.DataFrame:
        """印を付けた表（印・◎の期待値の帯・消 …）から、組の期待値（馬連・馬単・ワイド・3連複・3連単）と枠連の買い目を選ぶ。"""
        if not self._candidates:
            return pd.DataFrame(columns=list(COLUMNS))
        races = self._picker.races(marked)
        parts = [self._picker.select(rule, candidate, races) for rule, candidate in zip(self._picker.rules, self._candidates, strict=True)]
        if not self._bracket_candidates.empty and not self._frames.empty:
            parts.append(self._bracket.select(self._bracket_candidates, self._bracket.races(marked, self._frames)))
        parts = [part for part in parts if not part.empty]
        return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=list(COLUMNS))

    def _board(self, ticket_type, days: RaceDayRange, races: set[str]) -> pd.DataFrame:
        board = FinalOddsRepository(self._con, ticket_type).read(days)
        board = board[board["race_id"].astype(str).isin(races)]
        return pd.DataFrame({"race_id": board["race_id"].astype(str), "combo": board["combo"].astype(str), "odds": board["odds"].astype(float)})
