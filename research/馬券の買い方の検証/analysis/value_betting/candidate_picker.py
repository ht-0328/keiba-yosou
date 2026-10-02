"""枠A「馬を選ぶ」: 期待値が線以上の複勝を、レースごとに期待値の高い順に最大3点買う。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import columns as c
from .protocol import MAX_POINTS_PER_RACE, STAKE_YEN

_RACE_KEY = [c.WINDOW, c.PART, c.RACE_ID]
#: 払戻の表の値は 100円あたりの円。
_PAYOUT_PER_YEN = 100.0


class CandidatePicker:
    """期待値の付いた1頭ごとの表（``place_value``・``excluded`` の列を持つ）から、買い目を作る。

    消の馬と、期待値の無い馬（穴馬でない馬）は候補にしない。期待値が線以上の馬を、レースごとに期待値の高い順に
    ``max_points`` 点まで、1点 ``stake_yen`` 円で買う。線が決まっていない（NaN）なら何も買わない。
    買い目の表は、元の列に 賭け金・払戻（複勝の払戻 × 賭け金 ÷ 100円。外れは 0）・線 を足したもの。
    """

    def __init__(self, max_points: int = MAX_POINTS_PER_RACE, stake_yen: int = STAKE_YEN) -> None:
        self._max_points = max_points
        self._stake_yen = stake_yen

    def pick(self, valued: pd.DataFrame, line: float) -> pd.DataFrame:
        if np.isnan(line):
            return self._tickets(valued.iloc[0:0], line)
        excluded = valued[c.EXCLUDED].fillna(False).astype(bool)
        rows = valued[valued[c.PLACE_VALUE].notna() & (valued[c.PLACE_VALUE] >= line) & ~excluded]
        rank = rows.groupby(_RACE_KEY)[c.PLACE_VALUE].rank(method="first", ascending=False)
        return self._tickets(rows[rank <= self._max_points], line)

    def _tickets(self, rows: pd.DataFrame, line: float) -> pd.DataFrame:
        payout = rows[c.PLACE_PAYOUT].fillna(0.0).astype(float) * self._stake_yen / _PAYOUT_PER_YEN
        return rows.assign(**{c.STAKE_YEN: self._stake_yen, c.PAYOUT_YEN: payout.round().astype(int), c.LINE: line}) \
            .reset_index(drop=True)
