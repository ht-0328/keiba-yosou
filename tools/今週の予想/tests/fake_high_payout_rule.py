"""予想「高配当の組が当たるかを予想」の、買い目の決まりの偽物（テスト用。値は架空）。"""

from __future__ import annotations

import pandas as pd

from 今週の予想.ticket_rules import HIGH_PAYOUT_VALUE_LINE

#: 偽物の高配当の線（倍）。どの券種も同じ。
HIGH_LINE = 10.0


class FakeHighPayoutRule:
    """約束どおりの形の偽物。オッズが線以上で期待値が線以上の組を、券種ごとに確率の高い順に上限の点数まで。"""

    def __init__(self, max_points: int | None = None) -> None:
        self._max_points = max_points

    def pick(self, combos: pd.DataFrame) -> pd.DataFrame:
        chosen = combos[(combos["odds"] >= HIGH_LINE) & (combos["value"] >= HIGH_PAYOUT_VALUE_LINE)]
        if self._max_points is None:
            return chosen
        return chosen[chosen.groupby("ticket_type")["probability"].rank(ascending=False, method="first") <= self._max_points]
