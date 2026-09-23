"""単勝人気を帯にする。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 帯の名前（人気の範囲）。表に出す並びの順。
BANDS: tuple[str, ...] = ("1番人気", "2番人気", "3番人気", "4〜5番人気", "6〜9番人気", "10番人気以下")


class PopularityBand:
    """単勝人気（確定）を、表に出す帯（1・2・3・4〜5・6〜9・10〜）にする。人気が無ければ「不明」。"""

    def of(self, popularity: pd.Series) -> pd.Series:
        rank = pd.to_numeric(popularity, errors="coerce")
        labels = np.select(
            [rank == 1, rank == 2, rank == 3, rank.between(4, 5), rank.between(6, 9), rank >= 10],
            list(BANDS), default="不明",
        )
        return pd.Series(labels, index=popularity.index)
