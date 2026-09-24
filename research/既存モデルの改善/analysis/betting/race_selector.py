"""勝負するレースを選ぶ（1開催日の上位 N レースと重賞）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import RACE_DATE

from .race_columns import FAVORITE_EXCLUDED, GRADED, SCORE


class RaceSelector:
    """買う券種のあるレースから、1開催日ごとに上位 ``per_day`` レースと、重賞（上位の枠とは別）を選ぶ。

    並べ方は、1番人気を消したレース（本当に危険な1番人気がいるレース）を先に、そのあと券種全体の期待値の高い順。
    ``per_day`` が None なら全部選ぶ。例: ``per_day`` = 5 で、その日の重賞が上位5レースの外にあれば、6レースになる。
    """

    def __init__(self, per_day: int | None) -> None:
        self._per_day = per_day

    def select(self, races: pd.DataFrame) -> pd.Series:
        """レース単位の表（``SCORE`` の列を持つ）の行ごとに、勝負するか。"""
        if self._per_day is None:
            return pd.Series(True, index=races.index)
        ordered = races.sort_values([RACE_DATE, FAVORITE_EXCLUDED, SCORE], ascending=[True, False, False], kind="stable")
        rank = ordered.groupby(RACE_DATE).cumcount().reindex(races.index)
        return (rank < self._per_day) | races[GRADED]
