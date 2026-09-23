"""穴馬モデルの順で選ぶ。"""

from __future__ import annotations

from collections.abc import Collection

import pandas as pd

from ...column_names import HORSE_NO, LONGSHOT_PROB, LONGSHOT_ZONE, POPULARITY


class LongshotRankPicker:
    """穴馬モデルの「3着以内に入る確率」の高い順に選ぶ（穴馬だけ。同点は人気上位）。

    ``zone`` に「中穴」か「大穴」を渡すと、その区分の穴馬だけから選ぶ。
    """

    def __init__(self, zone: str | None = None) -> None:
        self._zone = zone

    def pick(self, runners: pd.DataFrame, count: int, taken: Collection[int]) -> list[int]:
        longshots = runners[runners[LONGSHOT_PROB].notna()]
        if self._zone is not None:
            longshots = longshots[longshots[LONGSHOT_ZONE] == self._zone]
        ordered = longshots.sort_values([LONGSHOT_PROB, POPULARITY], ascending=[False, True])
        return [int(horse) for horse in ordered[HORSE_NO] if horse not in taken][:max(count, 0)]
