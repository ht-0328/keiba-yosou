"""期待値の線を、検証期間の回収率で決める。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

#: 期待値の線の候補。
CANDIDATES: tuple[float, ...] = (1.0, 1.05, 1.1, 1.2, 1.3, 1.5)
#: 線を選ぶのに要る、検証期間で買った点の数の下限。
_MIN_POINTS = 100


class ThresholdChooser:
    """「期待値がこの値以上の馬を買う」の線を、検証期間の回収率がいちばん高くなるものに決める。

    買った点が 100 に満たない線は選ばない（少ない点のたまたまの大当たりで選ばないように）。
    テスト期間の結果は使わない。
    """

    def __init__(self, candidates: Sequence[float] = CANDIDATES, min_points: int = _MIN_POINTS) -> None:
        self._candidates = tuple(candidates)
        self._min_points = min_points

    def choose(self, expected_value: pd.Series, payout: pd.Series) -> float:
        """検証期間の期待値と払戻（100円あたり。外れは 0）から線を決める。どの線も条件に合わなければ NaN。"""
        rates = {threshold: self._rate(expected_value, payout, threshold) for threshold in self._candidates}
        valid = {threshold: rate for threshold, rate in rates.items() if not np.isnan(rate)}
        if not valid:
            return float("nan")
        return max(valid, key=valid.get)

    def _rate(self, expected_value: pd.Series, payout: pd.Series, threshold: float) -> float:
        bought = payout[expected_value >= threshold]
        if len(bought) < self._min_points:
            return float("nan")
        return float(bought.sum()) / (100.0 * len(bought))
