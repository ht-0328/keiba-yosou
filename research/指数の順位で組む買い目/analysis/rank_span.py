"""順位の範囲（例: 2〜8位、9位以下）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RankSpan:
    """レースの中の順位の範囲（両端を含む）。``high`` が None なら最下位まで（「9位以下」）。

    頭数が足りずに存在しない順位は ``ranks`` に出ない（その順位を使う組は買わない）。
    """

    low: int
    high: int | None = None

    def ranks(self, field: int) -> range:
        """頭数 ``field`` のレースで、この範囲にある順位。"""
        top = field if self.high is None else min(self.high, field)
        return range(self.low, top + 1)

    @property
    def label(self) -> str:
        if self.high is None:
            return f"{self.low}位以下"
        if self.high == self.low:
            return f"{self.low}位"
        return f"{self.low}〜{self.high}位"
