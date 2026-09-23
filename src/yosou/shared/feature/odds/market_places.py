"""出走の行から、単勝オッズから見た勝率・2着以内率・3着以内率を出す。"""

from __future__ import annotations

import pandas as pd

from .harville_places import HarvillePlaces
from .market_win_probability import MarketWinProbability


class MarketPlaces:
    """出走の行（``race_id``・``win_odds`` の列）から、オッズから見た勝率・2着以内率・3着以内率を出す。

    勝率を出す ``MarketWinProbability`` と、それを2着以内・3着以内に広げる ``HarvillePlaces`` を順に呼ぶだけ。
    同じレースの全頭の行が入っていることを前提にする（1頭でも欠けると、ほかの馬の値が変わる）。
    """

    def __init__(self) -> None:
        self._win = MarketWinProbability()
        self._places = HarvillePlaces()

    def of(self, entries: pd.DataFrame) -> pd.DataFrame:
        """列は ``WIN_RATE``・``TOP2_RATE``・``TOP3_RATE``。行の並びと index は ``entries`` と同じ。"""
        race_ids = entries["race_id"]
        return self._places.places(race_ids, self._win.of(race_ids, entries["win_odds"]))
