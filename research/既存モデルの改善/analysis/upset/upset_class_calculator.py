"""1レースの勝率と組み合わせのオッズから、券種ごとの荒れ具合の確率を出す。"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from yosou.upset_level.dataset import BetType, UpsetLevel, UpsetLevelRule

from ..market import RaceCombinations
from ..race_probability import FinishOrderProbability

#: 払戻は 100円あたり。確定オッズ × 100 が払戻になる。
_YEN_PER_ODDS = 100.0
#: 段階の数。
_LEVELS = len(UpsetLevel)


class UpsetClassCalculator:
    """1レースの勝率 ``p``（馬番 − 1 の位置に並べた配列）と、券種ごとの組み合わせ（``RaceCombinations``）から、
    券種ごとに「固い・中荒れ・大荒れ・超荒れ」の確率を出す。

    組み合わせが当たる確率は ``FinishOrderProbability``（単勝は勝率そのもの、馬連は順不同の1・2着、3連複は順不同の
    1〜3着、3連単は並び）。オッズの無い組み合わせ（無投票）は数えず、数えた分の合計で割って 1 にそろえる。
    """

    def __init__(self, rule: UpsetLevelRule) -> None:
        self._rule = rule

    def of_race(self, p: np.ndarray, order: FinishOrderProbability,
                combinations: Mapping[BetType, RaceCombinations]) -> dict[BetType, np.ndarray]:
        tables = self._tables(p, order)
        return {bet: self._levels(bet, tables[bet], found) for bet, found in combinations.items()}

    def _tables(self, p: np.ndarray, order: FinishOrderProbability) -> dict[BetType, np.ndarray]:
        """券種ごとの、組み合わせが当たる確率の表（馬番 − 1 で引く）。"""
        triple = order.ordered_triple(p)
        trio = (triple + triple.transpose(0, 2, 1) + triple.transpose(1, 0, 2)
                + triple.transpose(1, 2, 0) + triple.transpose(2, 0, 1) + triple.transpose(2, 1, 0))
        return {BetType.WIN: p, BetType.QUINELLA: order.quinella(p), BetType.TRIO: trio, BetType.TRIFECTA: triple}

    def _levels(self, bet: BetType, table: np.ndarray, found: RaceCombinations) -> np.ndarray:
        """1つの券種の4段階の確率。組み合わせが無ければ欠損値。"""
        if len(found) == 0:
            return np.full(_LEVELS, np.nan)
        probability = table[tuple((found.horses - 1).T)]
        yen = pd.Series(found.odds * _YEN_PER_ODDS)
        level = self._rule.levels_of(bet, yen).to_numpy().astype(int)
        weights = np.bincount(level, weights=probability, minlength=_LEVELS)
        total = weights.sum()
        return weights / total if total > 0 else np.full(_LEVELS, np.nan)
