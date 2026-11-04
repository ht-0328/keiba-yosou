"""組の市場の確率: 券種の確定オッズ（3連単・3連複）から、1 ÷ オッズ をレース内で合計 1 にそろえた、市場が見た組の確率を付ける。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

#: 付ける列。
MARKET = "market"


@dataclass(frozen=True)
class ComboMarket:
    """``odds``（``race_id``・``first``・``second``・``third``・``odds``）に ``market`` を足して返す。発売の無い組（オッズが無い）は含まれない。"""

    def attach(self, odds: pd.DataFrame) -> pd.DataFrame:
        inverse = 1.0 / odds["odds"]
        return odds.assign(**{MARKET: inverse / inverse.groupby(odds["race_id"]).transform("sum")})
