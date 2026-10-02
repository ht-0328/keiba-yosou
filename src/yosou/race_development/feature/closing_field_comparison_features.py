"""O. 同じレースの馬との比較（末脚）（3個）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import as_numbers

from .race_order_statistic import RaceOrderStatistic


class ClosingFieldComparisonFeatures:
    """O. このメンバーの中で、末脚があるほうか（設計書 09 の O）。``FieldFeatureGroup`` を守る。

    上がりの速さは小さいほど速いので、「いちばん末脚のある馬」は最小の値の馬である。
    """

    def __init__(self) -> None:
        self._order = RaceOrderStatistic()

    def build(self, entries: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        race = entries["race_id"]
        closing = as_numbers(features["近5走の上がりの速さの平均"])
        best_other = self._order.best_other(closing, race, largest=False)
        return pd.DataFrame({
            "近5走の上がりの速さの平均のレース内順位": closing.groupby(race).rank(method="min"),
            "ほかの馬の近5走の上がりの速さの平均の最小": best_other,
            "末脚がいちばんある相手との差": closing - best_other,
        }, index=entries.index)
