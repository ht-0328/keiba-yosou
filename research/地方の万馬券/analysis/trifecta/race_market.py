"""レースの市場の見立て: 単勝オッズから、馬ごとの支持率と 3着以内率、レースごとの 1〜3番人気の支持率と荒れ具合（市場の割れ方）を出す。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from yosou.shared.feature.odds import HarvillePlaces
from yosou.shared.feature.odds.column_names import TOP3_RATE

from ..payout_band import BIG, MEDIUM, SOLID

#: 付ける列。
SUPPORT, MARKET_TOP3, EDGE, TOP3_SUPPORT, MARKET_UPSET = "support", "market_top3", "edge", "top3_support", "market_upset"
#: 市場の割れ方で決める荒れ具合の線（1〜3番人気の支持率の合計）。段2 の表3 から。
SOLID_FROM, MEDIUM_FROM = 0.70, 0.55


@dataclass(frozen=True)
class RaceMarket:
    """``runners``（``race_id``・``popularity``・``win_odds``・``p3`` を持つ）に、支持率・市場の3着以内率・予想との差・レースの荒れ具合を足す。"""

    def attach(self, runners: pd.DataFrame) -> pd.DataFrame:
        table = runners.copy()
        inverse = 1.0 / table["win_odds"].replace(0, np.nan)
        table[SUPPORT] = inverse / inverse.groupby(table["race_id"]).transform("sum")
        table[MARKET_TOP3] = HarvillePlaces().places(table["race_id"], table[SUPPORT])[TOP3_RATE].to_numpy()
        table[EDGE] = table["p3"] - table[MARKET_TOP3]
        top3 = table[SUPPORT].where(table["popularity"] <= 3, 0.0)
        table[TOP3_SUPPORT] = top3.groupby(table["race_id"]).transform("sum")
        table[MARKET_UPSET] = self._upset(table[TOP3_SUPPORT])
        return table

    def _upset(self, top3_support: pd.Series) -> pd.Series:
        label = pd.Series(BIG, index=top3_support.index, dtype="object")
        label = label.mask(top3_support >= MEDIUM_FROM, MEDIUM)
        label = label.mask(top3_support >= SOLID_FROM, SOLID)
        return label
