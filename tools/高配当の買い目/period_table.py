"""探す期間と確かめる期間の回収率と的中数の表（表3）。"""

from __future__ import annotations

from itertools import chain, product
from typing import Any

import pandas as pd

from 共通.render import Table

from 高配当の買い目.number_text import rate_text
from 高配当の買い目.pick_groups import PickGroups
from 高配当の買い目.pick_numbers import PickNumbers
from 高配当の買い目.search_verify_periods import SearchVerifyPeriods


#: 期間ごとに並べる項目（``PeriodTable._cells`` の並びと同じ）。
_ITEMS: tuple[str, ...] = ("点数", "的中数", "回収率")


class PeriodTable:
    """券種ごと（最後に合計）の、探す期間・確かめる期間それぞれの 点数・的中数・回収率 の表。

    買い方は探す期間の成績を見て決めたので、決めたあとの成績は確かめる期間の列を見る。
    """

    def __init__(self, groups: PickGroups, periods: SearchVerifyPeriods) -> None:
        self._groups = groups
        self._periods = periods

    def table(self, picks: pd.DataFrame, note: str) -> Table:
        names = (self._periods.search_label, self._periods.verify_label)
        columns = ["券種", *(f"{name}の{item}" for name, item in product(names, _ITEMS))]
        rows = [self._row(label, group) for label, group in self._groups.of(picks)]
        return Table(columns, rows, title="3. 期間ごとの成績", note=note)

    def _row(self, label: str, picks: pd.DataFrame) -> list[Any]:
        by_period = [self._cells(PickNumbers(part)) for _, part in self._periods.split(picks)]
        return [label, *chain.from_iterable(by_period)]

    @staticmethod
    def _cells(numbers: PickNumbers) -> list[str]:
        return [f"{numbers.points:,}", f"{numbers.hits:,}", rate_text(numbers.rate)]
