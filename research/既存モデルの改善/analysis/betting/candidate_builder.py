"""期間の全レースの、買い目の候補をまとめる。"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from yosou.shared.dataset import HORSE_NO, RACE_ID
from yosou.shared.place_value import PlacePriceEstimator

from 馬券の買い方の検証.analysis.ticket import TicketType

from ..combined.horse_columns import WIN_PROBABILITY
from ..market import CombinationTable
from ..race_probability import FinishOrderProbability
from .betting_rule import RACE
from .race_candidate_builder import RaceCandidateBuilder
from .race_ticket_probabilities import RaceTicketProbabilities

#: 勝率を並べる配列の最小の長さ（中央競馬の最多頭数 18）。
_BOARD_SIZE = 18


class CandidateBuilder:
    """1頭ごとの表（組み合わせの勝率の列を持つ）から、期間の全レースの買い目の候補の表を作る。

    - ``tables``: 券種 → その期間の組み合わせと確定オッズ。
    - ``prices``: 複勝・ワイドの見込みの倍率（``PlacePriceEstimator``）。
    - ``order``: 着順の並びの確率を出す部品（検証期間で決めた Stern の補正）。
    """

    def __init__(self, tables: Mapping[TicketType, CombinationTable], prices: Mapping[TicketType, PlacePriceEstimator],
                 order: FinishOrderProbability) -> None:
        self._tables = dict(tables)
        self._race_builder = RaceCandidateBuilder(prices)
        self._probabilities = RaceTicketProbabilities(order)

    def build(self, horses: pd.DataFrame) -> pd.DataFrame:
        races = [self._race(str(race_id), group) for race_id, group in horses.groupby(RACE_ID, sort=False)]
        columns = list(races[0]) if races else []
        return pd.DataFrame({column: np.concatenate([race[column] for race in races]) for column in columns})

    def _race(self, race_id: str, group: pd.DataFrame) -> dict[str, np.ndarray]:
        probabilities = self._probabilities.of(self._board(group), len(group))
        combinations = {ticket: table.race(race_id) for ticket, table in self._tables.items()}
        candidates = self._race_builder.build(probabilities, combinations)
        count = len(next(iter(candidates.values())))
        return {RACE: np.full(count, race_id, dtype=object), **candidates}

    def _board(self, group: pd.DataFrame) -> np.ndarray:
        """勝率を、馬番 − 1 の位置に並べた配列。出走しない馬番は 0。"""
        numbers = group[HORSE_NO].to_numpy(dtype=int)
        board = np.zeros(max(_BOARD_SIZE, int(numbers.max())))
        board[numbers - 1] = group[WIN_PROBABILITY].to_numpy(dtype="float64")
        return board
