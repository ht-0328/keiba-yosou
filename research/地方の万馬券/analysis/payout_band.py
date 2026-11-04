"""配当の帯: 3連単の払戻（100円あたり、円）を 固い・中荒れ・大荒れ・超荒れ の4つに分ける。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

SOLID, MEDIUM, BIG, HUGE = "固い", "中荒れ", "大荒れ", "超荒れ"
#: 帯の並び順（表の行の順）。
PAYOUT_BANDS: tuple[str, ...] = (SOLID, MEDIUM, BIG, HUGE)


@dataclass(frozen=True)
class PayoutBand:
    """3連単の払戻 → 帯。線は地方の配当の分布から（1万円未満が 42%、1〜10万円が 45%、10〜100万円が 12%、100万円以上が 0.9%。11頭以上）。

    - 固い: ``medium_from`` 円未満（既定 1万円未満）
    - 中荒れ: ``medium_from`` 以上 ``big_from`` 未満（1万〜10万円。万馬券）
    - 大荒れ: ``big_from`` 以上 ``huge_from`` 未満（10万〜100万円。10万馬券）
    - 超荒れ: ``huge_from`` 以上（100万円以上）
    """

    medium_from: int = 10_000
    big_from: int = 100_000
    huge_from: int = 1_000_000

    def __post_init__(self) -> None:
        if not 0 < self.medium_from < self.big_from < self.huge_from:
            raise ValueError("配当の線は 固い < 中荒れ < 大荒れ < 超荒れ の順に大きくしてください")

    @property
    def label(self) -> str:
        """帯の決めごとを1行で。"""
        return (f"固い {self.medium_from:,}円未満・中荒れ {self.medium_from:,}〜{self.big_from:,}円・"
                f"大荒れ {self.big_from:,}〜{self.huge_from:,}円・超荒れ {self.huge_from:,}円以上")

    def band_of(self, payout: pd.Series) -> pd.Series:
        """払戻の列 → 帯の列。払戻が無い行は欠損値のまま。"""
        band = pd.Series(pd.NA, index=payout.index, dtype="string")
        band = band.mask(payout < self.medium_from, SOLID)
        band = band.mask(payout.between(self.medium_from, self.big_from - 1), MEDIUM)
        band = band.mask(payout.between(self.big_from, self.huge_from - 1), BIG)
        band = band.mask(payout >= self.huge_from, HUGE)
        return band
