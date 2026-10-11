"""表の材料（帯・市場から見た3着以内率・実際の3着以内）を、出走の表にそろえる。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import as_numbers
from yosou.shared.feature.odds import TOP3_RATE, MarketPlaces

from . import names
from .weight_bands import WeightBands

#: 3着以内とみなす着順（7頭以下のレースも3着以内で数える。展開スコアと同じ）。
_PLACES = 3


class WeightRuns:
    """``WeightRunRepository`` が読んだ出走の表に、3つの帯・市場から見た3着以内率（単勝オッズから Harville の式で）・3着以内（1 か 0）を足す。
    着順の無い馬（中止など）の3着以内は欠損値。"""

    def __init__(self) -> None:
        self._bands = WeightBands()
        self._market = MarketPlaces()

    def build(self, runs: pd.DataFrame) -> pd.DataFrame:
        """元の列に ``BANDS``・``MARKET_TOP3``・``TOP3`` を足した表。行の並びと index は ``runs`` と同じ。"""
        finish = as_numbers(runs["finish"])
        bands = self._bands.of(runs["weight_change"], runs["interval_days"], runs["age"])
        return pd.concat([runs, bands], axis=1).assign(**{
            names.MARKET_TOP3: self._market.of(runs)[TOP3_RATE],
            names.TOP3: (finish <= _PLACES).astype("float64").where(finish.notna()),
        })
