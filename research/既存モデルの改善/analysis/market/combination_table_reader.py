"""元DB から、1つの券種の組み合わせと確定オッズを期間ぶん読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.repository import FinalOddsRepository, RaceDayRange
from yosou.shared.repository.final_odds_repository import COMBO, ODDS, ODDS_HIGH

from .combination_table import CombinationTable

#: 組番の1頭ぶんの桁数（馬番2桁）。
_DIGITS = 2


class CombinationTableReader:
    """研究「馬券の買い方の検証」の ``FinalOddsRepository`` で確定オッズを読み、組番を馬番の整数に直す。"""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, ticket_type: TicketType, first_day: date, last_day: date) -> CombinationTable:
        raw = FinalOddsRepository(self._con, ticket_type).read(RaceDayRange(first_day, last_day))
        width = ticket_type.spec.horse_count
        combo = raw[COMBO].astype(str)
        horses = {f"h{position}": pd.to_numeric(combo.str.slice((position - 1) * _DIGITS, position * _DIGITS),
                                                errors="coerce")
                  for position in range(1, width + 1)}
        high = raw[ODDS_HIGH] if ODDS_HIGH in raw.columns else raw[ODDS]
        frame = pd.DataFrame({"race_id": raw["race_id"], **horses, "odds": raw[ODDS], "odds_high": high})
        return CombinationTable(frame.dropna(), width)
