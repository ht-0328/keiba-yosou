"""疑ったレースを条件ごとに分けて、◎と1番人気のどちらがよく来たかを出す。"""

from __future__ import annotations

import pandas as pd

from .top_pick_table import FAVORITE_SUFFIX

_FAVORITE_HIT = f"3着以内{FAVORITE_SUFFIX}"


class DoubtBreakdown:
    """``TopPickTable`` の表を ``column`` の値ごとに分ける。

    列は、レース数・疑った割合・疑ったレース数・疑ったレースの◎と1番人気の3着以内率・その差。
    差が負の条件は、疑うと外れやすい条件である。
    """

    def by(self, races: pd.DataFrame, column: str) -> pd.DataFrame:
        groups = races.groupby(column, observed=True)
        doubted = races[races["疑った"]].groupby(column, observed=True)
        table = pd.DataFrame({
            "レース": groups.size(), "疑った割合": groups["疑った"].mean(), "疑ったレース": doubted.size(),
            "疑ったレースの◎": doubted["3着以内"].mean(), "疑ったレースの1番人気": doubted[_FAVORITE_HIT].mean(),
        })
        table["差"] = table["疑ったレースの◎"] - table["疑ったレースの1番人気"]
        return table.round(3)
