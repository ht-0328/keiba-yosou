"""人気順位の範囲で選ぶ。"""

from __future__ import annotations

from collections.abc import Collection

import pandas as pd

from ...column_names import HORSE_NO, POPULARITY


class PopularityPicker:
    """確定の単勝人気が ``first``〜``last`` 番人気の馬を、人気の順に選ぶ（1〜3番人気、5・6番人気 など）。"""

    def __init__(self, first: int, last: int) -> None:
        if first < 1 or last < first:
            raise ValueError(f"人気順位の範囲が不正です: {first}〜{last}")
        self._first, self._last = first, last

    def pick(self, runners: pd.DataFrame, count: int, taken: Collection[int]) -> list[int]:
        inside = runners[runners[POPULARITY].between(self._first, self._last)]
        ordered = inside.sort_values(POPULARITY)
        return [int(horse) for horse in ordered[HORSE_NO] if horse not in taken][:max(count, 0)]
