"""1着の当たり具合（レースごとのログ損失）を測る。"""

from __future__ import annotations

import numpy as np
import pandas as pd


class RaceLogLoss:
    """レースごとに、勝った馬に付けた確率の −log を取る。小さいほど良い。

    1着が1頭に決まり、全頭にモデルと市場の確率があるレースだけで測る。モデルと市場（単勝オッズ）を同じレースで比べる。
    例: 勝った馬に 0.25 を付けていれば、そのレースのログ損失は −log(0.25) = 1.386。
    """

    def per_race(self, table: pd.DataFrame, probability: str) -> pd.DataFrame:
        race = table["race_id"]
        missing = (table[probability].isna() | table["market_win"].isna()).groupby(race).transform("sum")
        winners_in_race = table["won"].groupby(race).transform("sum")
        winners = table[(table["won"] == 1) & (winners_in_race == 1) & (missing == 0)]
        return pd.DataFrame({"race_id": winners["race_id"].to_numpy(),
                             "model": -np.log(winners[probability].clip(1e-6).to_numpy()),
                             "market": -np.log(winners["market_win"].clip(1e-6).to_numpy())})
