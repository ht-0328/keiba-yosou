"""確かめで分ける人気帯（人気馬・中穴・大穴）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class PopularityBand:
    """``name`` は表に出す名前、``first``・``last`` は確定の単勝人気の範囲（その人気を含む）。"""

    name: str
    first: int
    last: int

    def contains(self, popularity: pd.Series) -> pd.Series:
        return (popularity >= self.first) & (popularity <= self.last)


FAVORITE = PopularityBand("人気馬（1〜3番人気）", 1, 3)
MIDDLE = PopularityBand("中穴（4〜9番人気）", 4, 9)
LONGSHOT = PopularityBand("大穴（10番人気以下）", 10, 18)
OUTSIDERS = PopularityBand("中穴と大穴（4番人気以下）", 4, 18)
