"""同じ人気の馬全体の成績: 人気ごとの複勝率・複勝回収率・単勝回収率を数え、取り出した馬の人気の内訳で重み付けした「期待される値」を出す。"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

PLACE_RATE, PLACE_RETURN, WIN_RETURN = "複勝率", "複勝回収率", "単勝回収率"
_YEN_PER_POINT = 100.0


@dataclass
class PopularityBaseline:
    """``fit`` で母集団（ある期間の全出走）から人気ごとの成績を数え、``expected`` で部分集合の「同じ人気の馬全体」の成績を返す。"""

    rates: pd.DataFrame = field(default_factory=pd.DataFrame)

    def fit(self, table: pd.DataFrame) -> "PopularityBaseline":
        """``table`` は出走の行（``popularity``・``finish``・``place_payout``・``win_payout``）。"""
        placed = (table["finish"] <= 3).astype(float)
        frame = pd.DataFrame({
            "popularity": table["popularity"], PLACE_RATE: placed,
            PLACE_RETURN: table["place_payout"] / _YEN_PER_POINT, WIN_RETURN: table["win_payout"] / _YEN_PER_POINT,
        })
        self.rates = frame.groupby("popularity")[[PLACE_RATE, PLACE_RETURN, WIN_RETURN]].mean()
        return self

    def expected(self, subset: pd.DataFrame) -> dict[str, float]:
        """``subset`` の馬と同じ人気の馬全体の成績（人気の内訳で重み付けした平均）。"""
        matched = self.rates.reindex(subset["popularity"])
        return {name: float(matched[name].mean()) for name in (PLACE_RATE, PLACE_RETURN, WIN_RETURN)}

    def actual(self, subset: pd.DataFrame) -> dict[str, float]:
        """``subset`` そのものの成績。"""
        return {
            PLACE_RATE: float((subset["finish"] <= 3).mean()),
            PLACE_RETURN: float(subset["place_payout"].mean() / _YEN_PER_POINT),
            WIN_RETURN: float(subset["win_payout"].mean() / _YEN_PER_POINT),
        }
