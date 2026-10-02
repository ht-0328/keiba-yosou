"""1つの区切りで、荒れ具合を計算で出す。"""

from __future__ import annotations

from collections.abc import Mapping
from itertools import chain

import numpy as np
import pandas as pd

from yosou.shared.dataset import HORSE_NO, RACE_ID
from yosou.upset_level.dataset import BetType, UpsetLevel

from ..combined import RaceProbabilityBuilder
from ..combined.horse_columns import WIN_PROBABILITY
from ..market import CombinationTable
from ..race_probability import FinishOrderProbability
from ..walk_forward import PART, PART_TEST, PART_VALID, WINDOW
from ..windows import TestWindow
from .upset_class_calculator import UpsetClassCalculator

#: 予測の表の列の名前（方法・券種）。
METHOD, BET = "方法", "券種"
#: 勝率を並べる配列の最小の長さ（中央競馬の最多頭数 18）。
_BOARD_SIZE = 18


class UpsetCalculationRunner:
    """1つの区切りで、検証期間の行で勝率の出し方（``RaceProbabilityBuilder``）を決め、テスト期間の全レースについて、
    券種ごとの4段階の確率を計算で出す。

    ``method`` は表に出す方法の名前（例: 計算・オッズだけ）。``tables`` は券種 → テスト期間の組み合わせと確定オッズ。
    """

    def __init__(self, calculator: UpsetClassCalculator, builder: RaceProbabilityBuilder, method: str) -> None:
        self._calculator = calculator
        self._builder = builder
        self._method = method

    def run(self, horses: pd.DataFrame, window: TestWindow,
            tables: Mapping[BetType, CombinationTable]) -> tuple[pd.DataFrame, dict[str, object]]:
        """（予測の表, 勝率の出し方の記録）。予測の表は 1行 = 1レース × 1券種 で、4段階の確率を持つ。"""
        valid = horses[horses[PART] == PART_VALID]
        test = horses[horses[PART] == PART_TEST]
        fit = self._builder.fit(valid)
        chosen = test.assign(**{WIN_PROBABILITY: fit.win_probability(test)})
        order = fit.order_probability()
        races = [self._race(str(race_id), group, order, tables, window)
                 for race_id, group in chosen.groupby(RACE_ID, sort=False)]
        record = {WINDOW: window.name, METHOD: self._method, **fit.summary()}
        return pd.DataFrame(list(chain.from_iterable(races))), record

    def _race(self, race_id: str, group: pd.DataFrame, order: FinishOrderProbability,
              tables: Mapping[BetType, CombinationTable], window: TestWindow) -> list[dict[str, object]]:
        combinations = {bet: table.race(race_id) for bet, table in tables.items()}
        levels = self._calculator.of_race(self._board(group), order, combinations)
        return [self._row(window, race_id, bet, values) for bet, values in levels.items()]

    def _board(self, group: pd.DataFrame) -> np.ndarray:
        """勝率を、馬番 − 1 の位置に並べた配列。出走しない馬番は 0。"""
        numbers = group[HORSE_NO].to_numpy(dtype=int)
        board = np.zeros(max(_BOARD_SIZE, int(numbers.max())))
        board[numbers - 1] = group[WIN_PROBABILITY].to_numpy(dtype="float64")
        return board

    def _row(self, window: TestWindow, race_id: str, bet: BetType, values: np.ndarray) -> dict[str, object]:
        by_level = {level.label: float(values[level.value]) for level in UpsetLevel}
        return {WINDOW: window.name, METHOD: self._method, RACE_ID: race_id, BET: bet.label, **by_level}
