"""本命の確率の積（対象5レースの本命の、そろえた1着の確率のかけ算）を出す。"""

from __future__ import annotations

import math
from collections.abc import Sequence

import pandas as pd

from ..leg import SHARE


class FavoriteProduct:
    """設計書 15 の 13。各対象レースの本命（そろえた1着の確率が最大の馬）の確率を5つかけた値。買い目に依らない、その日の値で、
    5レースの本命が全部勝つ組の当たる確率と同じ。多く買う日か少なく買う日かを決める材料（``BudgetTierJudge``）。"""

    def of(self, legs: Sequence[pd.DataFrame]) -> float:
        """``legs`` は5レースの確率の表（``RaceWinShare`` の結果。全頭）。"""
        if not legs:
            raise ValueError("対象レースの確率の表がありません")
        return math.prod(float(leg[SHARE].max()) for leg in legs)
