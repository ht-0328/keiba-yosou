"""事例の型に当てはまるレースを、決まった数だけ選ぶ。"""

from __future__ import annotations

import pandas as pd

from .case_pattern import CasePattern


class CasePicker:
    """型に当てはまるレースから、``count`` レースを無作為に選ぶ（``seed`` が同じなら同じレース）。

    珍しいレースだけに偏らないよう、極端なものから選ばずに無作為に選ぶ。選んだレースは開催日の順に並べる。
    """

    def __init__(self, count: int, seed: int) -> None:
        self._count = count
        self._seed = seed

    def pick(self, races: pd.DataFrame, pattern: CasePattern) -> pd.DataFrame:
        matched = races[pattern.matches(races).fillna(False).astype(bool)]
        picked = matched.sample(n=min(self._count, len(matched)), random_state=self._seed)
        return picked.sort_values(["race_date", "race_id"])
