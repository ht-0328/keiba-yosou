"""同じオッズの馬全体の成績: 単勝オッズの帯ごとの複勝率・複勝回収率・単勝回収率を数え、取り出した馬のオッズの内訳で重み付けした「期待される値」を出す。

同じ人気（``PopularityBaseline``）より細かい。人気の順位は同じでもオッズが違えば市場の見立ては違うので、
「オッズで分かること以上に、その事情が効いているか」はこちらで見る。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .popularity_baseline import PLACE_RATE, PLACE_RETURN, WIN_RETURN

#: 単勝オッズの帯の境目（倍）。
ODDS_EDGES: tuple[float, ...] = (0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0, 15.0, 20.0, 30.0, 50.0, 100.0, np.inf)
_YEN_PER_POINT = 100.0


@dataclass
class OddsBaseline:
    """``fit`` で母集団からオッズの帯ごとの成績を数え、``expected`` で部分集合の「同じオッズの馬全体」の成績を返す。"""

    rates: pd.DataFrame = field(default_factory=pd.DataFrame)

    def fit(self, table: pd.DataFrame) -> "OddsBaseline":
        frame = pd.DataFrame({
            "band": self._band(table), PLACE_RATE: (table["finish"] <= 3).astype(float),
            PLACE_RETURN: table["place_payout"] / _YEN_PER_POINT, WIN_RETURN: table["win_payout"] / _YEN_PER_POINT,
        })
        self.rates = frame.groupby("band", observed=True)[[PLACE_RATE, PLACE_RETURN, WIN_RETURN]].mean()
        return self

    def expected(self, subset: pd.DataFrame) -> dict[str, float]:
        matched = self.rates.reindex(self._band(subset))
        return {name: float(matched[name].mean()) for name in (PLACE_RATE, PLACE_RETURN, WIN_RETURN)}

    def _band(self, table: pd.DataFrame) -> pd.Series:
        return pd.cut(table["win_odds"], ODDS_EDGES, right=False, labels=False)
