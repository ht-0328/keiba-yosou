"""表 G の材料（脚質・ペース・市場から見た3着以内率・実際の3着以内）を、出走の表にそろえる。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import as_numbers
from yosou.shared.feature.odds import TOP3_RATE, MarketPlaces

from . import names
from .pre_race_style import PreRaceStyle
from .result_pace import ResultPace

#: 3着以内とみなす着順（7頭以下のレースも3着以内で数える。研究「展開の理論の検証」と同じ）。
_PLACES = 3


class AdvantageRuns:
    """``DevelopmentRunRepository`` が読んだ出走の表に、脚質（レース前）・ペース（結果）・市場から見た3着以内率・
    3着以内（1 か 0）と、表 G の鍵（競馬場コード・芝ダ）を足す。

    市場から見た3着以内率は、単勝オッズから見た勝率を Harville の式で3着以内に広げたもの（``MarketPlaces``。
    全頭の予想の出発点と同じ物差し）。着順の無い馬（中止など）の3着以内は欠損値。
    """

    def __init__(self) -> None:
        self._style = PreRaceStyle()
        self._pace = ResultPace()
        self._market = MarketPlaces()

    def build(self, runs: pd.DataFrame) -> pd.DataFrame:
        """元の列に ``names.STYLE``・``names.PACE``・``names.MARKET_TOP3``・``names.TOP3``・``names.VENUE_CODE``・``names.SURFACE``
        を足した表。行の並びと index は ``runs`` と同じ。"""
        finish = as_numbers(runs["finish"])
        return runs.assign(**{
            names.STYLE: self._style.of(runs),
            names.PACE: runs["race_id"].map(self._pace.of(runs)),
            names.MARKET_TOP3: self._market.of(runs)[TOP3_RATE],
            names.TOP3: (finish <= _PLACES).astype("float64").where(finish.notna()),
            names.VENUE_CODE: runs["venue_code"].astype(str),
            names.SURFACE: runs["surface"].astype(str),
        })
