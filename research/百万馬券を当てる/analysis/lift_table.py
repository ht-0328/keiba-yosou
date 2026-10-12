"""切り口の値ごとに、事象（帯のレース・人気薄の3着以内など）がどれだけ集まったかを数える。"""

from __future__ import annotations

import pandas as pd

#: 出す表の列の名前。
COUNT, HITS, RATE, LIFT = "数", "当てはまった数", "割合", "集まり方"


class LiftTable:
    """切り口の値ごとに、数・事象に当てはまった数・割合・集まり方（その値の割合 ÷ 全体の割合）を並べる。

    ``flag`` は事象の列（真偽か 0/1）。数の列は分位で ``bins`` 個に区切り、文字の列（と値が少ない数の列）は値のまま分ける。
    数が ``min_count`` に満たない値の行は、割合が当てにならないので落とす。
    """

    def __init__(self, flag: str, bins: int = 5, min_count: int = 30, max_values: int = 12) -> None:
        self._flag = flag
        self._bins = bins
        self._min_count = min_count
        self._max_values = max_values

    def table(self, frame: pd.DataFrame, column: str) -> pd.DataFrame:
        base = frame[self._flag].astype(float).mean()
        groups = frame.groupby(self.labels(frame[column]), observed=True)[self._flag]
        table = groups.agg(**{COUNT: "size", HITS: "sum"})
        table[RATE] = table[HITS] / table[COUNT]
        table[LIFT] = table[RATE] / base if base > 0 else float("nan")
        table.index.name = column
        return table[table[COUNT] >= self._min_count]

    def labels(self, values: pd.Series) -> pd.Series:
        """値ごとの分け方の名前（値のままか、分位の区間）。2つの表を同じ区切りで比べるときは、先にこれで名前にしておく。"""
        is_number = pd.api.types.is_numeric_dtype(values)
        if not is_number or values.nunique() <= self._max_values:
            return values.astype("string").fillna("（無し）")
        return pd.qcut(values, self._bins, duplicates="drop").astype("string").fillna("（無し）")
