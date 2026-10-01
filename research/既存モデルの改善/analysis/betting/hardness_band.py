"""勝負するレースを、レースの堅さ（軸の3着以内の確率）の帯で絞る条件。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class HardnessBand:
    """軸の3着以内の確率が ``lower`` 以上・``upper`` 未満のレースだけを勝負の候補にする条件。

    None の端は区切らない。両方 None なら全部のレース。例: ``HardnessBand(0.7, None)`` は「軸の確率 0.7 以上
    （予想が迷わず1頭を選べている堅いレース）」、``HardnessBand(None, 0.6)`` は「0.6 未満（予想が迷っているレース）」。
    軸の確率が欠損のレースは、全部のレースの条件でだけ入る。
    """

    lower: float | None = None
    upper: float | None = None

    def contains(self, probability: pd.Series) -> pd.Series:
        """レースごとに、帯に入るか。"""
        inside = pd.Series(True, index=probability.index)
        if self.lower is not None:
            inside &= probability >= self.lower
        if self.upper is not None:
            inside &= probability < self.upper
        return inside.fillna(False).astype(bool)

    @property
    def label(self) -> str:
        """表に出す名前（例 軸の確率 0.7 以上）。"""
        if self.lower is None and self.upper is None:
            return "全部のレース"
        if self.upper is None:
            return f"軸の確率 {self.lower:g} 以上"
        if self.lower is None:
            return f"軸の確率 {self.upper:g} 未満"
        return f"軸の確率 {self.lower:g} 以上 {self.upper:g} 未満"


#: 全部のレース（堅さで絞らない）。
ALL_RACES = HardnessBand()

#: 検証期間で選ばせる堅さの帯の候補。堅い側（0.6・0.7・0.8 以上）と、迷う側（0.6・0.7 未満）の両方を置き、
#: どちらが良いかも検証期間で決める。0.8 以上は、研究「一番人気を疑う」で◎が1番人気と同じくらい来た帯。
HARDNESS_BANDS: tuple[HardnessBand, ...] = (
    ALL_RACES, HardnessBand(0.6, None), HardnessBand(0.7, None), HardnessBand(0.8, None),
    HardnessBand(None, 0.6), HardnessBand(None, 0.7),
)
