"""穴馬モデルの確率の値で選ぶ。"""

from __future__ import annotations

from collections.abc import Collection

import pandas as pd

from ...column_names import HORSE_NO, LONGSHOT_PROB, POPULARITY, WIN_ODDS


class LongshotProbabilityPicker:
    """穴馬モデルの「3着以内に入る確率」が ``threshold`` 以上の穴馬を、確率の高い順に全部選ぶ。

    順位ではなく値で絞るので、レースによって0頭にも何頭にもなる。``odds_range`` を渡すと、
    単勝オッズがその帯（両端を含む）の馬だけにする（ルール集 TAN-01 の 10〜19.9倍 など）。
    """

    def __init__(self, threshold: float, odds_range: tuple[float, float] | None = None) -> None:
        self._threshold = threshold
        self._odds_range = odds_range

    def pick(self, runners: pd.DataFrame, count: int, taken: Collection[int]) -> list[int]:
        rows = runners[runners[LONGSHOT_PROB] >= self._threshold]
        if self._odds_range is not None:
            low, high = self._odds_range
            rows = rows[rows[WIN_ODDS].between(low, high)]
        ordered = rows.sort_values([LONGSHOT_PROB, POPULARITY], ascending=[False, True])
        return [int(horse) for horse in ordered[HORSE_NO] if horse not in taken][:max(count, 0)]
