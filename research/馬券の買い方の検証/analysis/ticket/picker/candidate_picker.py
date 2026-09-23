"""候補の選び方の決まり。"""

from __future__ import annotations

from collections.abc import Collection
from typing import Protocol

import pandas as pd


class CandidatePicker(Protocol):
    """1レースの runners（``column_names.py`` の列）から、列に置く馬番を選ぶ。

    ``taken`` に入っている馬番は選ばない（先の列で使った馬）。候補が足りなければ、あるだけ返す。
    """

    def pick(self, runners: pd.DataFrame, count: int, taken: Collection[int]) -> list[int]:
        ...
