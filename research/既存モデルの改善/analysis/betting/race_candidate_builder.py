"""1レースの買い目ごとの期待値を出し、候補を作る。"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from yosou.shared.place_value import PlacePriceEstimator

from 馬券の買い方の検証.analysis.ticket import TicketType

from ..market import RaceCombinations
from .betting_rule import COMBO, ODDS, PRICE, PROBABILITY, TICKET, VALUE
from .rule_grid import MAX_ODDS, MIN_VALUE

#: 候補の表の、1頭目の馬番の列（単勝・複勝の人気を引くのに使う）。
FIRST_HORSE = "1頭目の馬番"


class RaceCandidateBuilder:
    """1レースの、券種ごとの買い目（組み合わせ）について、当たる確率・見込みの倍率・期待値を出す。

    見込みの倍率は、複勝・ワイドでは最低オッズ × 帯ごとの倍率（``prices``）、ほかの券種では確定オッズそのもの。
    期待値 = 当たる確率 × 見込みの倍率（1 で元返し）。どの買い方の候補にもならない買い目（期待値が
    ``MIN_VALUE`` 未満か、オッズが券種の上限より高い）は落とす。結果は列 → 配列の辞書（速さのため、表にするのは呼ぶ側）。
    """

    def __init__(self, prices: Mapping[TicketType, PlacePriceEstimator]) -> None:
        self._prices = dict(prices)

    def build(self, probabilities: Mapping[TicketType, np.ndarray],
              combinations: Mapping[TicketType, RaceCombinations]) -> dict[str, np.ndarray]:
        parts = [self._one(ticket, probabilities[ticket], found) for ticket, found in combinations.items()]
        return {column: np.concatenate([part[column] for part in parts]) for column in parts[0]}

    def _one(self, ticket: TicketType, table: np.ndarray, found: RaceCombinations) -> dict[str, np.ndarray]:
        probability = table[tuple((found.horses - 1).T)] if len(found) else np.zeros(0)
        price = self._price(ticket, found.odds)
        value = probability * price
        keep = (value >= MIN_VALUE) & (found.odds <= MAX_ODDS[ticket])
        horses = found.horses[keep]
        return {
            TICKET: np.full(int(keep.sum()), ticket.label, dtype=object),
            COMBO: self._combo_text(horses),
            FIRST_HORSE: horses[:, 0] if len(horses) else np.zeros(0, dtype=int),
            PROBABILITY: probability[keep], ODDS: found.odds[keep], PRICE: price[keep], VALUE: value[keep],
        }

    def _price(self, ticket: TicketType, odds: np.ndarray) -> np.ndarray:
        """見込みの倍率。複勝・ワイドは最低オッズから見積もり、ほかは確定オッズのまま。"""
        estimator = self._prices.get(ticket)
        if estimator is None:
            return odds
        return estimator.estimate_array(odds)

    def _combo_text(self, horses: np.ndarray) -> np.ndarray:
        """馬番の並びを、払戻の表と同じ組番の文字列（2桁ずつ）にする。"""
        if len(horses) == 0:
            return np.zeros(0, dtype=object)
        digits = [np.char.zfill(horses[:, position].astype(str), 2) for position in range(horses.shape[1])]
        text = digits[0]
        for column in digits[1:]:
            text = np.char.add(text, column)
        return text.astype(object)
