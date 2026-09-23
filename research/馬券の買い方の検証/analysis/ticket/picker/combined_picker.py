"""いくつかの選び方を順に当てる。"""

from __future__ import annotations

from collections.abc import Collection, Sequence

import pandas as pd

from .candidate_picker import CandidatePicker


class CombinedPicker:
    """（選び方, 頭数）の並びを順に当てて、1つの列にする（「近走2位 1頭 + 穴馬上位 2頭」のような列）。

    先に選んだ馬は、あとの選び方では選ばない。``count`` は合計の上限。
    """

    def __init__(self, parts: Sequence[tuple[CandidatePicker, int]]) -> None:
        if not parts:
            raise ValueError("選び方が1つもありません")
        self._parts = tuple(parts)

    def pick(self, runners: pd.DataFrame, count: int, taken: Collection[int]) -> list[int]:
        chosen: list[int] = []
        for picker, part_count in self._parts:
            chosen += picker.pick(runners, part_count, {*taken, *chosen})
        return chosen[:max(count, 0)]
