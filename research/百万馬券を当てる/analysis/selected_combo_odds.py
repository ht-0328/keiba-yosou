"""選んだレースの、3連単・3連複の組ごとの確定オッズを読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.dataset import RACE_DATE, RACE_ID
from yosou.shared.repository import FinalOddsRepository, RaceDayRange
from yosou.shared.repository.final_odds_repository import COMBO, ODDS

#: 組番の1頭ぶんの桁数（馬番2桁）。
_DIGITS = 2


class SelectedComboOdds:
    """共通の ``FinalOddsRepository`` で、選んだレースのある年ごとに確定オッズを読み、選んだレースの行だけ残す。

    返すのは レースID → 組（馬番の並び。3連複は小さい順）→ オッズ。
    1年ぶんずつ読むのは、3連単の組の数が1年で数百万行になり、全期間を一度に読むと重いため。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, ticket_type: TicketType, races: pd.DataFrame) -> dict[str, dict[tuple[int, ...], float]]:
        wanted = set(races[RACE_ID])
        years = sorted(int(year) for year in races[RACE_DATE].dt.year.unique())
        found: dict[str, dict[tuple[int, ...], float]] = {}
        for year in years:
            found.update(self._year(ticket_type, year, wanted))
        return found

    def _year(self, ticket_type: TicketType, year: int, wanted: set[str]) -> dict[str, dict[tuple[int, ...], float]]:
        raw = FinalOddsRepository(self._con, ticket_type).read(RaceDayRange(date(year, 1, 1), date(year, 12, 31)))
        raw = raw[raw["race_id"].isin(wanted) & raw[ODDS].notna()]
        print(f"  {ticket_type.value} {year}年: {raw['race_id'].nunique()}レースのオッズを読みました", flush=True)
        combos = raw[COMBO].astype(str).map(_horses)
        return {race_id: dict(zip(combos[rows.index], rows[ODDS])) for race_id, rows in raw.groupby("race_id")}


def _horses(text: str) -> tuple[int, ...]:
    """組番（馬番を2桁ずつ並べた文字列）を馬番の組にする。"""
    return tuple(int(text[start:start + _DIGITS]) for start in range(0, len(text), _DIGITS))
