"""過去走を、出走の行ごとに新しい順に横に並べる。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from yosou.shared.feature.history import AsOfLookup, DatedRecords

#: 横に並べた列の名前の形（列名_何走前。0 がいちばん新しい走）。
_LAG_NAME = "{column}_{lag}"


class RunLags:
    """出走の行ごとに、その馬の開催日の前日までの過去走を、新しい順に ``count`` 走ぶん横に並べる。

    例: 馬A が 6月1日に出走するなら、馬A の 5月31日までの走のうち新しい 10走の値（1走前・2走前…）。
    近5走の平均のように今回のレースによらないものだけでなく、「今回と同じ芝ダの走だけの平均」や「今回の開催日からの
    日数で重みを付けた平均」のように、今回のレースによって変わるものを計算するために使う。
    同じ日や、あとの日の走は引かない（リークを防ぐ決まり。共通の ``AsOfLookup``）。
    """

    def __init__(self, count: int) -> None:
        self._count = count

    def of(self, entries: pd.DataFrame, runs: pd.DataFrame, columns: Sequence[str]) -> dict[str, np.ndarray]:
        """``runs`` は過去走（列 ``horse_id``・``race_date``・``race_id`` と ``columns``）。数える走だけに絞ってから渡す。

        戻り値は 列名 → 行列（出走の行の数 × ``count``。列 0 がいちばん新しい走）。走が足りなければ欠損値。
        """
        ordered = runs.sort_values(["horse_id", "race_date", "race_id"], kind="stable").reset_index(drop=True)
        horses = ordered.groupby("horse_id", sort=False)
        lagged = {
            _LAG_NAME.format(column=column, lag=lag): horses[column].shift(lag)
            for column in columns for lag in range(self._count)
        }
        table = pd.DataFrame(lagged).assign(horse_id=ordered["horse_id"], race_date=ordered["race_date"])
        found = AsOfLookup(entries, "horse_id").latest(DatedRecords(table, "horse_id", "race_date"), days_before=1)
        return {column: self._matrix(found, column) for column in columns}

    def _matrix(self, found: pd.DataFrame, column: str) -> np.ndarray:
        """1つの列の、出走の行の数 × ``count`` の行列。"""
        names = [_LAG_NAME.format(column=column, lag=lag) for lag in range(self._count)]
        return found[names].to_numpy()
