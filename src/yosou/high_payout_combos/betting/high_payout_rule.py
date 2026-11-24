"""買い目の決まり。"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from yosou.shared.betting import TicketType

from ..dataset import DEFAULT_VALUE_LINE, PayoutBand
from ..dataset.column_names import ODDS, PROBABILITY, RACE_ID, TICKET_TYPE


class HighPayoutRule:
    """確率の付いた組の表から、買う組を選ぶ。

    買うのは「オッズが高配当の線以上・上限未満で、期待値（確率 × オッズ）が期待値の線以上」の組。
    例: 馬連（線 30倍・上限 1,000倍）で、45倍・確率 0.025 の組は期待値 1.125 なので買う。25倍の組は線より下なので買わない。
    ``max_points`` を渡すと、1レース・1券種につき確率の高い順にその点数まで（省略すると上限なし）。帯の無い券種の組は選ばない。
    """

    def __init__(self, bands: Mapping[TicketType, PayoutBand], value_line: float = DEFAULT_VALUE_LINE,
                 max_points: int | None = None) -> None:
        self._bands = bands
        self._value_line = value_line
        self._max_points = max_points

    def pick(self, combos: pd.DataFrame) -> pd.DataFrame:
        """``combos`` の列は ``ticket_type``（``TicketType`` の label）・``odds``・``probability`` ほか（1レースの予測の結果か、年ごとの予測）。

        買う組の行だけを、列と並びを変えずに返す。点数の上限をレースごとに数えるには ``race_id`` の列が要る（無ければ表の全体で数える）。
        """
        value = combos[PROBABILITY] * combos[ODDS]
        picked = combos[self._is_high_payout(combos) & (value >= self._value_line)]
        if self._max_points is None:
            return picked
        return self._most_likely(picked)

    def _is_high_payout(self, combos: pd.DataFrame) -> np.ndarray:
        """行ごとに、その券種の高配当の線以上・上限未満のオッズか。"""
        is_high = np.zeros(len(combos), dtype=bool)
        for ticket_type, band in self._bands.items():
            is_high |= ((combos[TICKET_TYPE] == ticket_type.label) & band.is_high_payout(combos[ODDS])).to_numpy(dtype=bool)
        return is_high

    def _most_likely(self, picked: pd.DataFrame) -> pd.DataFrame:
        """1レース・1券種につき、確率の高い順に ``max_points`` 点まで。"""
        keys = [name for name in (RACE_ID, TICKET_TYPE) if name in picked.columns]
        order = picked.groupby(keys)[PROBABILITY].rank(ascending=False, method="first")
        return picked[order <= self._max_points]
