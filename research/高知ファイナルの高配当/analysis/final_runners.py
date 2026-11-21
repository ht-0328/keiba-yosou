"""ファイナルレースの出走馬の表: 材料つきの高知の出走からファイナルの行を取り出し、レースの中での順位・人気の帯・回収率の列を付ける。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .final_race import FINAL
from .popularity_band import PopularityBand

_RACE = "race_id"
_YEN_PER_POINT = 100.0
#: 「前に行く馬」とみなす、近3走の4コーナーの相対位置の上限。
FRONT_POSITION = 0.3


@dataclass(frozen=True)
class FinalRunners:
    """``min_heads`` 頭以上のファイナルレースの出走馬。順位は小さいほど前（着差は小さいほど上）で、同じ値は同じ順位。"""

    min_heads: int = 9
    popularity: PopularityBand = PopularityBand()

    def select(self, runs: pd.DataFrame) -> pd.DataFrame:
        table = runs[runs[FINAL] & (runs["field_size"] >= self.min_heads)].copy()
        race = table.groupby(_RACE)
        table["corner4_rank_in_race"] = race["corner4_rel_recent3"].rank(method="min")
        table["corner1_rank_in_race"] = race["corner1_rel_recent3"].rank(method="min")
        table["time_diff_rank_in_race"] = race["time_diff_recent3"].rank(method="min")
        is_front = (table["corner4_rel_recent3"] <= FRONT_POSITION).astype(int)
        table["front_runners"] = is_front.groupby(table[_RACE]).transform("sum")
        table["band"] = self.popularity.band_of(table["popularity"])
        table["win_return"] = table["win_payout"].fillna(0) / _YEN_PER_POINT
        table["place_return"] = table["place_payout"].fillna(0) / _YEN_PER_POINT
        return table
