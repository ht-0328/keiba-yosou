"""レースごとに、券種ごとの買い目の候補を作り、当たる確率・確定オッズ・見込みの倍率・期待値を付ける。"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence

import numpy as np
import pandas as pd

from yosou.shared.dataset import HORSE_NO, RACE_ID
from yosou.shared.place_value import PlacePriceEstimator

from yosou.shared.betting import TicketType

from ..combined.horse_columns import WIN_PROBABILITY
from ..market import CombinationTable
from ..race_probability import FinishOrderProbability
from ..ticket_combos import TICKET_SPECS, RaceHorses, TicketSpec
from .candidate_columns import COMBO, FIRST_HORSE, GROUP, ODDS, PRICE, PROBABILITY, RACE, TICKET, VALUE
from .race_ticket_probabilities import RaceTicketProbabilities

#: 勝率を並べる配列の最小の長さ（中央競馬の最多頭数 18）。
_BOARD_SIZE = 18
#: 候補の表の列の並び。
COLUMNS = [RACE, TICKET, COMBO, FIRST_HORSE, GROUP, PROBABILITY, ODDS, PRICE, VALUE]


class RaceCandidatePricer:
    """役割の付いた1頭ごとの表（組み合わせの勝率の列も持つ）から、券種ごとの買い目の候補（``TicketSpec.combos``）を作り、
    当たる確率（Stern の補正つき Harville の式）・確定オッズ・見込みの倍率・期待値を付ける。確定オッズの無い候補は落とす。

    ``upset_races`` は荒れそうなレースのID（馬連・ワイド・馬単で穴-穴も候補にする）。
    期待値のカット・賭け金・券種全体の値は、確率を補正してから付ける（``ProbabilityCalibrator``・``TicketSetBuilder``）。
    """

    def __init__(self, tables: Mapping[TicketType, CombinationTable], prices: Mapping[TicketType, PlacePriceEstimator],
                 order: FinishOrderProbability, specs: Sequence[TicketSpec] = TICKET_SPECS) -> None:
        self._tables = dict(tables)
        self._prices = dict(prices)
        self._probabilities = RaceTicketProbabilities(order)
        self._specs = tuple(specs)

    def build(self, horses: pd.DataFrame, upset_races: Collection[str]) -> pd.DataFrame:
        upset = set(upset_races)
        races = [self._race(str(race_id), group, str(race_id) in upset) for race_id, group in horses.groupby(RACE_ID, sort=False)]
        frames = [frame for frame in races if not frame.empty]
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=COLUMNS)

    def _race(self, race_id: str, group: pd.DataFrame, upset: bool) -> pd.DataFrame:
        horses = RaceHorses.of(group)
        if not horses.runners:
            return pd.DataFrame(columns=COLUMNS)
        probabilities = self._probabilities.of(self._board(group), len(group))
        parts = [self._priced(race_id, spec, horses, upset, probabilities[spec.ticket]) for spec in self._specs]
        kept = [part for part in parts if not part.empty]
        return pd.concat(kept, ignore_index=True) if kept else pd.DataFrame(columns=COLUMNS)

    def _priced(self, race_id: str, spec: TicketSpec, horses: RaceHorses, upset: bool, table: np.ndarray) -> pd.DataFrame:
        """候補のうち確定オッズのあるものに、当たる確率・オッズ・見込みの倍率・期待値を付けた表。"""
        found = self._tables[spec.ticket].race(race_id)
        positions = {tuple(numbers): index for index, numbers in enumerate(found.horses.tolist())}
        combos = [(combo, group) for combo, group in spec.combos.of(horses, upset) if combo in positions]
        if not combos:
            return pd.DataFrame(columns=COLUMNS)
        numbers = np.array([combo for combo, _ in combos], dtype=int)
        odds = found.odds[[positions[combo] for combo, _ in combos]]
        probability = table[tuple((numbers - 1).T)]
        price = self._price(spec.ticket, odds)
        return pd.DataFrame({
            RACE: race_id, TICKET: spec.ticket.label, COMBO: ["".join(f"{number:02d}" for number in combo) for combo, _ in combos],
            FIRST_HORSE: numbers[:, 0], GROUP: [group for _, group in combos], PROBABILITY: probability, ODDS: odds,
            PRICE: price, VALUE: probability * price,
        })

    def _price(self, ticket: TicketType, odds: np.ndarray) -> np.ndarray:
        estimator = self._prices.get(ticket)
        return odds if estimator is None else estimator.estimate_array(odds)

    def _board(self, group: pd.DataFrame) -> np.ndarray:
        """勝率を、馬番 − 1 の位置に並べた配列。出走しない馬番は 0。"""
        numbers = group[HORSE_NO].to_numpy(dtype=int)
        board = np.zeros(max(_BOARD_SIZE, int(numbers.max())))
        board[numbers - 1] = group[WIN_PROBABILITY].to_numpy(dtype="float64")
        return board
