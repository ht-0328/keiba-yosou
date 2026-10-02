"""複勝の見込みの倍率を、区切りごとに、その区切りより前の払戻で決める。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.place_value import PlacePriceEstimator

from 既存モデルの改善.analysis.windows import TestWindow

from . import columns as c


class PlacePriceFitter:
    """区切りごとに、検証期間の始まりより前の全頭の払戻（``Round3Materials.price_history``）で ``PlacePriceEstimator`` を学ぶ。

    最低オッズの帯ごとの倍率に、オッズの幅（最高 ÷ 最低）の帯の倍率も掛ける（穴馬の設計書 15 の 18。今の穴馬の予想と同じ）。
    テスト期間と検証期間の払戻は使わない。
    """

    def __init__(self, price_history: pd.DataFrame) -> None:
        self._history = price_history

    def for_window(self, window: TestWindow) -> PlacePriceEstimator:
        before = self._history[self._history[c.RACE_DATE] < pd.Timestamp(window.valid_first_day)]
        return PlacePriceEstimator().fit(before[c.PLACE_ODDS], before[c.PLACE_PAYOUT].fillna(0.0), before[c.PLACE_ODDS_HIGH])
