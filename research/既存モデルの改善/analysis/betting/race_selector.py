"""勝負するレースを選ぶ（1開催日の上位 N レースと重賞）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import RACE_DATE

from .race_columns import CONFIDENCE, GRADED


class RaceSelector:
    """1開催日ごとに、◎の自信が高い上位 ``per_day`` レースと、重賞（上位の枠とは別）を選ぶ。

    ``per_day`` が None なら、全レースを選ぶ。例: ``per_day`` = 5 で、その日の重賞が上位5レースの外にあれば、6レースになる。
    """

    def __init__(self, per_day: int | None) -> None:
        self._per_day = per_day

    @property
    def per_day(self) -> int | None:
        return self._per_day

    def select(self, races: pd.DataFrame) -> pd.Series:
        """レース単位の表の行ごとに、勝負するか。"""
        if self._per_day is None:
            return pd.Series(True, index=races.index)
        rank = races.groupby(RACE_DATE)[CONFIDENCE].rank(method="first", ascending=False)
        return (rank <= self._per_day).fillna(False) | races[GRADED]
