"""買い目の決まり（予想のパッケージの ``HighPayoutRule``）の偽物（テスト用。値は架空）。"""

from __future__ import annotations

import pandas as pd

#: 偽物の高配当の線（倍）。
HIGH_LINE = 10.0


class FakePickRule:
    """買い目の決まりの偽物。オッズが線以上で期待値が線以上の組を、1レース・1券種につき確率の高い順に上限の点数まで。"""

    def __init__(self, value_line: float, max_points: int | None) -> None:
        self._value_line = value_line
        self._max_points = max_points

    def pick(self, combos: pd.DataFrame) -> pd.DataFrame:
        picked = combos[(combos["odds"] >= HIGH_LINE) & (combos["probability"] * combos["odds"] >= self._value_line)]
        if self._max_points is None:
            return picked
        return picked[picked.groupby(["race_id", "ticket_type"])["probability"].rank(ascending=False, method="first") <= self._max_points]
