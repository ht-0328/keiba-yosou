"""買ったレースで、1レースに何点買うことになるかの分かれ方。"""

from __future__ import annotations

import pandas as pd


class BetsPerRaceDistribution:
    """1レースの点数ごとの、レースの数と割合。入力の列: rid（1行 = 1点）。"""

    def table(self, bought: pd.DataFrame) -> pd.DataFrame:
        per_race = bought.groupby("rid").size()
        counts = per_race.value_counts().sort_index()
        return pd.DataFrame({
            "1レースの点数": counts.index,
            "レースの数": counts.to_numpy(),
            "割合": (counts / counts.sum()).round(3).to_numpy(),
        })
