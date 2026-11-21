"""同じ人気の馬の成績: 人気ごとの3着以内率と勝率を数え、取り出した馬たちに「同じ人気なら何頭来るはずか」を返す。"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

PLACE, WIN = "placed", "won"


@dataclass
class SamePopularityRates:
    """``fit`` で母集団（ファイナルレースの全出走馬）から人気ごとの率を数え、``expected`` で部分集合の見込みの頭数を返す。"""

    rates: pd.DataFrame = field(default_factory=pd.DataFrame)

    def fit(self, table: pd.DataFrame) -> "SamePopularityRates":
        """``table`` は出走馬の行（``popularity``・``placed``・``won``）。"""
        self.rates = table.groupby("popularity")[[PLACE, WIN]].mean()
        return self

    def expected(self, subset: pd.DataFrame, outcome: str) -> float:
        """``subset`` の馬が同じ人気の馬と同じ率で来たときの、3着以内（``PLACE``）か1着（``WIN``）の頭数。"""
        return float(subset["popularity"].map(self.rates[outcome]).sum())
