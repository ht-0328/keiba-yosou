"""レースごとの「荒れそうな確率」（3連複の中荒れ以上の確率）を出す。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.dataset import HORSE_NO, RACE_ID
from yosou.upset_level.dataset import BetType, UpsetLevel, UpsetLevelRule


from ..combined.horse_columns import WIN_PROBABILITY
from ..market import CombinationTable
from ..race_probability import FinishOrderProbability
from ..upset import UpsetClassCalculator

#: 勝率を並べる配列の最小の長さ（中央競馬の最多頭数 18）。
_BOARD_SIZE = 18


class RaceUpsetProbability:
    """荒れ具合の予想のうち、比べ方でいちばん当たった「3つの予想から計算する方法」で、レースごとに
    3連複が中荒れ以上（払戻 3,000円以上）になる確率を出す。組み合わせの勝率と、3連複の確定オッズから計算する。"""

    def __init__(self, trio: CombinationTable, order: FinishOrderProbability) -> None:
        self._trio = trio
        self._order = order
        self._calculator = UpsetClassCalculator(UpsetLevelRule())

    def of(self, horses: pd.DataFrame) -> pd.Series:
        """レースID → 中荒れ以上の確率（3連複のオッズが無いレースは欠損値）。"""
        values = {str(race_id): self._race(str(race_id), group) for race_id, group in horses.groupby(RACE_ID, sort=False)}
        return pd.Series(values, dtype="float64")

    def _race(self, race_id: str, group: pd.DataFrame) -> float:
        numbers = group[HORSE_NO].to_numpy(dtype=int)
        board = np.zeros(max(_BOARD_SIZE, int(numbers.max())))
        board[numbers - 1] = group[WIN_PROBABILITY].to_numpy(dtype="float64")
        levels = self._calculator.of_race(board, self._order, {BetType.TRIO: self._trio.race(race_id)})[BetType.TRIO]
        return float(1.0 - levels[UpsetLevel.SOLID.value])


