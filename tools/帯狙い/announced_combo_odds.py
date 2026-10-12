"""1レースの3連単・3連複の組ごとのオッズを、締め切り前（なければ確定）の断面で読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.repository import AnnouncedTicketOddsRepository, FinalOddsRepository, RaceDayRange
from yosou.shared.repository.final_odds_repository import COMBO, ODDS

#: 組番の1頭ぶんの桁数（馬番2桁）。
_DIGITS = 2


class AnnouncedComboOdds:
    """締め切り前のオッズのいちばん新しい断面（``AnnouncedTicketOddsRepository``）から、組（馬番の並び）→ オッズ を作る。

    締め切り前のオッズが無く、確定オッズがあるレース（終わったレース）は、確定オッズ（``FinalOddsRepository``）を使う。
    どちらも無ければ空（買い目の金額を決められないので、組だけを出す）。3連複の組は馬番の小さい順。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, race_id: str, ticket_type: TicketType) -> dict[tuple[int, ...], float]:
        board = AnnouncedTicketOddsRepository(self._con, ticket_type).read(race_id)
        if board.empty:
            board = self._final(race_id, ticket_type)
        board = board[board[ODDS].notna()]
        return {_horses(str(combo)): float(odds) for combo, odds in zip(board[COMBO], board[ODDS])}

    def _final(self, race_id: str, ticket_type: TicketType) -> pd.DataFrame:
        day = date(int(race_id[:4]), int(race_id[4:6]), int(race_id[6:8]))
        final = FinalOddsRepository(self._con, ticket_type).read(RaceDayRange(day, day))
        return final[final["race_id"].eq(race_id)]


def _horses(text: str) -> tuple[int, ...]:
    """組番（馬番を2桁ずつ並べた文字列）を馬番の組にする。"""
    return tuple(int(text[start:start + _DIGITS]) for start in range(0, len(text), _DIGITS))
