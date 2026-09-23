"""材料表（races と runners）を持つ値。"""

from __future__ import annotations

from datetime import date

import pandas as pd

from ..column_names import RACE_DATE, RACE_ID


class RaceMaterials:
    """買い目を作るのに要る材料。1行 = 1レースの ``races`` と、1行 = 1頭の ``runners``（列は ``column_names.py``）。

    レースごとの runners は ``runners_of`` で引く（レースID で分けておく）。
    """

    def __init__(self, races: pd.DataFrame, runners: pd.DataFrame) -> None:
        self._races = races.reset_index(drop=True)
        self._runners = runners.reset_index(drop=True)
        self._by_race: dict[str, pd.DataFrame] = {
            race_id: rows for race_id, rows in self._runners.groupby(RACE_ID, sort=False)
        }

    @property
    def races(self) -> pd.DataFrame:
        return self._races

    @property
    def runners(self) -> pd.DataFrame:
        return self._runners

    @property
    def race_ids(self) -> list[str]:
        """レースID の並び（races の順）。"""
        return list(self._races[RACE_ID])

    def runners_of(self, race_id: str) -> pd.DataFrame:
        """そのレースの出走馬の行。無ければ空の表。"""
        rows = self._by_race.get(race_id)
        return rows if rows is not None else self._runners.iloc[0:0]

    def between(self, first_day: date, last_day: date) -> RaceMaterials:
        """開催日が ``first_day`` 以上 ``last_day`` 以下のレースだけにした材料。"""
        first, last = pd.Timestamp(first_day), pd.Timestamp(last_day)
        races = self._races[(self._races[RACE_DATE] >= first) & (self._races[RACE_DATE] <= last)]
        runners = self._runners[self._runners[RACE_ID].isin(races[RACE_ID])]
        return RaceMaterials(races, runners)
