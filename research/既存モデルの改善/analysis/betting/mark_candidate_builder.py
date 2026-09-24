"""印のルールで作った買い目に、当たる確率・オッズ・期待値を付ける。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from yosou.shared.dataset import HORSE_NO, RACE_ID
from yosou.shared.place_value import PlacePriceEstimator

from 馬券の買い方の検証.analysis.ticket import TicketType

from ..combined.horse_columns import WIN_PROBABILITY
from ..market import CombinationTable
from ..marks.mark import MARK, Mark
from ..marks.mark_rule import MarkRule
from ..marks.mark_rules import MARK_RULES
from ..race_probability import FinishOrderProbability
from .candidate_columns import COMBO, COVER, FIRST_HORSE, ODDS, PRICE, PROBABILITY, RACE, TICKET, VALUE
from .race_ticket_probabilities import RaceTicketProbabilities

#: 勝率を並べる配列の最小の長さ（中央競馬の最多頭数 18）。
_BOARD_SIZE = 18
#: 候補の表の列の並び。
_COLUMNS = [RACE, TICKET, COMBO, FIRST_HORSE, PROBABILITY, ODDS, PRICE, VALUE, COVER]


class MarkCandidateBuilder:
    """印の付いた1頭ごとの表（組み合わせの勝率の列も持つ）から、印のルール（``MARK_RULES``）で買い目を作り、
    買い目ごとに当たる確率・確定オッズ・見込みの倍率・期待値を付けた表にする。

    - 当たる確率は、組み合わせの勝率から Stern の補正つき Harville の式で出す（``RaceTicketProbabilities``）。
    - 見込みの倍率は、複勝・ワイドでは最低オッズ × 帯ごとの倍率（``prices``）、ほかは確定オッズのまま。
    - 確定オッズの無い買い目（発売が無い・取消の馬を含む）は落とす。◎の無いレースは買い目を作らない。
    期待値の線でのカットはここではしない（線は検証期間で決める。``MarkPlan``）。
    """

    def __init__(self, tables: Mapping[TicketType, CombinationTable], prices: Mapping[TicketType, PlacePriceEstimator],
                 order: FinishOrderProbability, rules: Sequence[MarkRule] = MARK_RULES) -> None:
        self._tables = dict(tables)
        self._prices = dict(prices)
        self._probabilities = RaceTicketProbabilities(order)
        self._rules = tuple(rules)

    def build(self, horses: pd.DataFrame) -> pd.DataFrame:
        races = [self._race(str(race_id), group) for race_id, group in horses.groupby(RACE_ID, sort=False)]
        frames = [frame for frame in races if not frame.empty]
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=_COLUMNS)

    def _race(self, race_id: str, group: pd.DataFrame) -> pd.DataFrame:
        horses_of = self._horses_of(group)
        if Mark.HONMEI not in horses_of:
            return pd.DataFrame(columns=_COLUMNS)
        probabilities = self._probabilities.of(self._board(group), len(group))
        parts = [self._rule(race_id, rule, horses_of, probabilities[rule.ticket]) for rule in self._rules]
        return pd.concat([part for part in parts if not part.empty] or [pd.DataFrame(columns=_COLUMNS)], ignore_index=True)

    def _horses_of(self, group: pd.DataFrame) -> dict[Mark, tuple[int, ...]]:
        """印 → その印の馬番の並び（印の無い印は入れない）。"""
        marked = group[group[MARK].notna()]
        numbers = {mark: tuple(marked.loc[marked[MARK] == mark.value, HORSE_NO].astype(int)) for mark in Mark}
        return {mark: found for mark, found in numbers.items() if found}

    def _rule(self, race_id: str, rule: MarkRule, horses_of: Mapping[Mark, tuple[int, ...]],
              table: np.ndarray) -> pd.DataFrame:
        """1つのルールの買い目のうち、確定オッズのあるもの。"""
        found = self._tables[rule.ticket].race(race_id)
        positions = {tuple(horses): index for index, horses in enumerate(found.horses.tolist())}
        combos = [combo for combo in rule.combos(horses_of) if combo in positions]
        if not combos:
            return pd.DataFrame(columns=_COLUMNS)
        horses = np.array(combos, dtype=int)
        odds = found.odds[[positions[combo] for combo in combos]]
        probability = table[tuple((horses - 1).T)]
        price = self._price(rule.ticket, odds)
        return pd.DataFrame({
            RACE: race_id, TICKET: rule.ticket.label, COMBO: ["".join(f"{number:02d}" for number in combo) for combo in combos],
            FIRST_HORSE: horses[:, 0], PROBABILITY: probability, ODDS: odds, PRICE: price, VALUE: probability * price,
            COVER: rule.cover,
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
