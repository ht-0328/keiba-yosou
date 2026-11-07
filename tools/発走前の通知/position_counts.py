"""3着以内に来た馬が、4コーナーで前・中・後ろのどこにいたかの頭数。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PositionCounts:
    """``races`` は数えたレースの数、``top3`` は3着以内の頭数、``front``・``middle``・``back`` はそのうち
    4コーナーで頭数の前3分の1・真ん中・後ろ3分の1にいた頭数。"""

    races: int
    top3: int
    front: int
    middle: int
    back: int

    @property
    def front_share(self) -> float:
        return self.front / self.top3 if self.top3 else 0.0

    @property
    def middle_share(self) -> float:
        return self.middle / self.top3 if self.top3 else 0.0

    @property
    def back_share(self) -> float:
        return self.back / self.top3 if self.top3 else 0.0
