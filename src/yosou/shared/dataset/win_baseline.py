"""目的変数「1着」の基準を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..feature import PredictionTiming
from ..feature.odds import MarketWinProbability

#: 確率をロジットにするときの端の丸め（0 と 1 はロジットにできない）。
_EDGE = 1e-4


class WinBaseline:
    """1着の基準 = オッズから見た勝率（単勝オッズの逆数をレース内で合計 1 にそろえた値）のロジット。``TargetBaseline`` を守る。

    近走と適性の予想の1着のモデルが使う（設計書 10・15 の 14）。3着以内のモデルの ``Top3Baseline`` と同じく、
    オッズが分かるのは前日から（木曜は基準なしで学ぶ）。オッズの無い馬（無投票など）は、頭数から見た割合（1 ÷ 頭数）を基準にする。
    """

    def __init__(self) -> None:
        self._win = MarketWinProbability()

    @property
    def known_from(self) -> PredictionTiming:
        return PredictionTiming.DAY_BEFORE

    def build(self, entries: pd.DataFrame) -> pd.Series:
        """``entries`` は同じレースの全頭の行（列 ``race_id``・``win_odds``）。行の並びと index は ``entries`` と同じ。"""
        win = self._win.of(entries["race_id"], entries["win_odds"])
        field_size = entries.groupby("race_id")["race_id"].transform("size")
        filled = win.fillna(1.0 / field_size)
        clipped = filled.clip(_EDGE, 1.0 - _EDGE)
        return np.log(clipped / (1.0 - clipped))
