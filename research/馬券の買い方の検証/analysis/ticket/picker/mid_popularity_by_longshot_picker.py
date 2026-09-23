"""人気順位の範囲の中を、穴馬モデルの順で選ぶ。"""

from __future__ import annotations

from collections.abc import Collection

import pandas as pd

from ...column_names import HORSE_NO, LONGSHOT_PROB, POPULARITY


class MidPopularityByLongshotPicker:
    """人気が ``first``〜``last`` 番人気の馬を、穴馬モデルの「3着以内に入る確率」の高い順に選ぶ（確率の無い馬は後ろ）。

    3連単の「待ちのフォーメーション」（3〜9番人気の中穴4頭。SRT-P01）に使う。
    """

    def __init__(self, first: int, last: int) -> None:
        if first < 1 or last < first:
            raise ValueError(f"人気順位の範囲が不正です: {first}〜{last}")
        self._first, self._last = first, last

    def pick(self, runners: pd.DataFrame, count: int, taken: Collection[int]) -> list[int]:
        inside = runners[runners[POPULARITY].between(self._first, self._last)]
        ordered = inside.sort_values([LONGSHOT_PROB, POPULARITY], ascending=[False, True], na_position="last")
        return [int(horse) for horse in ordered[HORSE_NO] if horse not in taken][:max(count, 0)]
