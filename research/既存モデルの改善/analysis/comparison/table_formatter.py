"""pandas の表を、出力の表にする。"""

from __future__ import annotations

import math

import pandas as pd

from 共通.render import Table

#: 丸める桁数。
_DIGITS = 4


class TableFormatter:
    """pandas の表を ``共通.render.Table`` にする。小数は4桁に丸め、欠損値は空欄にする。"""

    def table(self, frame: pd.DataFrame, title: str, note: str = "") -> Table:
        rows = [[self._cell(value) for value in row] for row in frame.itertuples(index=False)]
        return Table([str(column) for column in frame.columns], rows, title=title, note=note)

    def _cell(self, value: object) -> object:
        if isinstance(value, float) and math.isnan(value):
            return None
        if isinstance(value, float):
            return round(value, _DIGITS)
        return value
