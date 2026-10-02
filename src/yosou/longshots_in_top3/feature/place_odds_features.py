"""M. 複勝オッズから見た評価（4個）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import EntryRecords, as_numbers
from yosou.shared.feature.odds import TOP3_RATE, MarketPlaces

from .place_market_rate import PlaceMarketRate
from .place_odds_catalog import PLACE_MARKET_RATE, PLACE_ODDS_HIGH_FEATURE, PLACE_ODDS_LOW_FEATURE, PLACE_TO_WIN_RATIO


class PlaceOddsFeatures:
    """M. 複勝オッズから見た評価（設計書 09 の M）。``FeatureGroup`` を守る。

    複勝の最低・最高オッズそのものと、そこから出した複勝オッズから見た3着以内率（``PlaceMarketRate``）、
    それを単勝オッズから見た3着以内率（Harville の式。K と同じ値）で割った比。比が 1 より大きい馬は、
    「勝つとまでは見られていないが、3着以内には来ると見られている」馬である。
    期待値の高い馬に残る偏り（期待値で選ぶと、モデルが複勝の市場より高く見積もった馬が集まる）を、
    複勝の市場の見立てをモデルに渡して直すために足した（設計書 15 の 16）。
    複勝オッズは出走の行の ``place_odds_low``・``place_odds_high``（``PlaceOddsRepository`` が読む）。
    無い馬（木曜・無投票）は欠損値。
    """

    def __init__(self) -> None:
        self._place_rate = PlaceMarketRate()
        self._win_places = MarketPlaces()

    def build(self, records: EntryRecords) -> pd.DataFrame:
        entries = records.entries
        place_rate = self._place_rate.of(entries)
        win_top3 = self._win_places.of(entries)[TOP3_RATE]
        return pd.DataFrame({
            PLACE_ODDS_LOW_FEATURE: as_numbers(entries["place_odds_low"]),
            PLACE_ODDS_HIGH_FEATURE: as_numbers(entries["place_odds_high"]),
            PLACE_MARKET_RATE: place_rate,
            PLACE_TO_WIN_RATIO: place_rate / win_top3.where(win_top3 > 0),
        }, index=entries.index)
