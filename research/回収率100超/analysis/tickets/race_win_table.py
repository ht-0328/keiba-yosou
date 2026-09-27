"""レースごとに、馬番の順に並べた勝率を引けるようにする。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .ticket_kind import MAX_HORSES


class RaceWinTable:
    """1行 = 1頭の勝率の表を、「レース → 馬番の順の勝率 18個」の形にする。

    出走しない馬番（取消・除外・もともと居ない番号）は 0。1レースの合計は 1。
    例: 3頭立てで 1番 0.5・2番 0.3・3番 0.2 なら、[0.5, 0.3, 0.2, 0, 0, …, 0]。
    """

    def __init__(self, rid: pd.Series, horse_no: pd.Series, win_probability: pd.Series) -> None:
        valid = win_probability.notna() & horse_no.between(1, MAX_HORSES)
        codes, races = pd.factorize(rid[valid])
        self._row_of = pd.Series(np.arange(len(races)), index=races)
        self._table = np.zeros((len(races), MAX_HORSES))
        self._table[codes, horse_no[valid].to_numpy(dtype=np.int64) - 1] = win_probability[valid]
        totals = self._table.sum(axis=1, keepdims=True)
        self._table = np.divide(self._table, totals, out=np.zeros_like(self._table), where=totals > 0)

    def get(self, rid: int) -> np.ndarray | None:
        """そのレースの勝率 18個。予測の無いレースは None。"""
        row = self._row_of.get(rid)
        return None if row is None else self._table[row]
