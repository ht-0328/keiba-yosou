"""人気の帯: 単勝人気を 人気馬・中穴・大穴 の3つに分ける。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

#: 帯の名前（表に出す1文字と、読むときの名前）。
FAVORITE, MIDDLE, LONGSHOT = "人", "中", "大"
BAND_NAMES: dict[str, str] = {FAVORITE: "人気馬", MIDDLE: "中穴", LONGSHOT: "大穴"}


@dataclass(frozen=True)
class PopularityBand:
    """人気 → 帯。地方は頭数が少ないので、人気馬は 1〜3番人気、中穴は 4〜7番人気、それ以外（8番人気以下）を大穴とする（利用者の指示）。

    ``middle_low``・``middle_high`` で中穴の範囲を変えられる（4〜6 など）。人気馬は 1 〜 ``middle_low`` − 1。
    """

    middle_low: int = 4
    middle_high: int = 7

    def __post_init__(self) -> None:
        if not 2 <= self.middle_low <= self.middle_high:
            raise ValueError(f"中穴の範囲が正しくありません: {self.middle_low}-{self.middle_high}")

    @property
    def label(self) -> str:
        """帯の決めごとを1行で（表の注に使う）。"""
        return (f"人気馬 1〜{self.middle_low - 1}番人気・中穴 {self.middle_low}〜{self.middle_high}番人気・"
                f"大穴 {self.middle_high + 1}番人気以下")

    def band_of(self, popularity: pd.Series) -> pd.Series:
        """人気の列 → 帯の列（人・中・大）。人気が無い行は欠損値のまま。"""
        band = pd.Series(pd.NA, index=popularity.index, dtype="string")
        band = band.mask(popularity < self.middle_low, FAVORITE)
        band = band.mask(popularity.between(self.middle_low, self.middle_high), MIDDLE)
        band = band.mask(popularity > self.middle_high, LONGSHOT)
        return band
