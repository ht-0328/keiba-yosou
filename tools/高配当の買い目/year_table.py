"""年ごとの回収率と的中数の表（表2）。"""

from __future__ import annotations

import pandas as pd

from 共通.render import Table

from 高配当の買い目.number_text import rate_text
from 高配当の買い目.pick_columns import RACE_DATE
from 高配当の買い目.pick_groups import PickGroups
from 高配当の買い目.pick_numbers import PickNumbers


class YearTable:
    """券種ごと（最後に合計）× 年の、回収率と的中数の表。セルは ``回収率（的中数）``（例 ``112.3%（45）``）。買った点の無い年は ``-（0）``。"""

    def __init__(self, groups: PickGroups) -> None:
        self._groups = groups

    def table(self, picks: pd.DataFrame, years: list[int], note: str) -> Table:
        rows = [self._row(label, group, years) for label, group in self._groups.of(picks)]
        return Table(["券種", *(f"{year}年" for year in years)], rows, title="2. 年ごとの回収率（かっこは的中数）", note=note)

    def _row(self, label: str, picks: pd.DataFrame, years: list[int]) -> list[str]:
        return [label, *(self._cell(picks, year) for year in years)]

    @staticmethod
    def _cell(picks: pd.DataFrame, year: int) -> str:
        numbers = PickNumbers(picks[pd.to_datetime(picks[RACE_DATE]).dt.year == year])
        return f"{rate_text(numbers.rate)}（{numbers.hits:,}）"
