"""単勝オッズから見た勝率。"""

from __future__ import annotations

import pandas as pd

#: 出力の列の名前。
MARKET_WIN = "オッズから見た勝率"


class MarketWinProbability:
    """単勝オッズの逆数を、レースの中で合計 1 にそろえた値を足す（馬の力を、市場がどう見ていたか）。

    例: オッズ 2.0・4.0・4.0 の3頭なら、逆数 0.5・0.25・0.25 で、合計 1 なのでそのまま。
    オッズが無い馬は欠損値で、そのレースの合計にも入れない。
    """

    def build(self, runners: pd.DataFrame) -> pd.DataFrame:
        odds = pd.to_numeric(runners["win_odds"], errors="coerce")
        inverse = (1.0 / odds).where(odds > 0)
        total = inverse.groupby(runners["race_id"]).transform("sum")
        return runners.assign(**{MARKET_WIN: inverse / total})
