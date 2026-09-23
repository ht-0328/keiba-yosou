"""近走と適性モデルの順で選ぶ。"""

from __future__ import annotations

from collections.abc import Collection

import pandas as pd

from ...column_names import FORM_PROB, HORSE_NO, POPULARITY


class FormRankPicker:
    """近走と適性モデルの「3着以内に入る確率」の高い順に選ぶ（同点は人気上位）。

    ``skip`` は、順位の上位を飛ばす数（1 なら本命を飛ばして2位から。対抗の列に使う）。
    飛ばすのは ``taken`` を除く前の順位で数える。
    """

    def __init__(self, skip: int = 0) -> None:
        self._skip = skip

    def pick(self, runners: pd.DataFrame, count: int, taken: Collection[int]) -> list[int]:
        ordered = runners.sort_values([FORM_PROB, POPULARITY], ascending=[False, True], na_position="last")
        ranked = list(ordered[HORSE_NO])[self._skip:]
        return [int(horse) for horse in ranked if horse not in taken][:max(count, 0)]
