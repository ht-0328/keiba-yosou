"""目的変数「3着以内」の基準を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..feature import PredictionTiming
from ..feature.odds import TOP3_RATE, MarketPlaces

#: 確率をロジットにするときの端の丸め（0 と 1 はロジットにできない）。
_EDGE = 1e-4
#: 3着以内に入る頭数。オッズの無い馬の基準は、頭数から見た割合（3 ÷ 頭数）にする。
_PLACES = 3.0


class Top3Baseline:
    """3着以内の基準 = オッズから見た3着以内率（Harville の式）のロジット。``TargetBaseline`` を守る。

    近走と適性の予想（全頭）と穴馬の予想が使う。オッズが分かるのは前日から（木曜は基準なしで学ぶ）。
    オッズの無い馬（無投票など）は、頭数から見た割合（3 ÷ 頭数）を基準にする。
    """

    def __init__(self) -> None:
        self._places = MarketPlaces()

    @property
    def known_from(self) -> PredictionTiming:
        return PredictionTiming.DAY_BEFORE

    def build(self, entries: pd.DataFrame) -> pd.Series:
        top3 = self._places.of(entries)[TOP3_RATE]
        field_size = entries.groupby("race_id")["race_id"].transform("size")
        filled = top3.fillna(np.minimum(_PLACES / field_size, 1.0))
        clipped = filled.clip(_EDGE, 1.0 - _EDGE)
        return np.log(clipped / (1.0 - clipped))
