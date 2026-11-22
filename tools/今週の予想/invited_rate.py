"""中央の過去走が無い招待馬の、過去の同じ種類の馬の成績から見た確率。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InvitedRate:
    """1頭の評価（``InvitedRates.rate`` が作る）。

    ``kind`` は招待の種類（外国招待・地方招待）、``win``・``top3`` は1着になる確率・3着以内に入る確率、
    ``runs`` は数えた過去の初出走の数、``win_factor``・``top3_factor`` は同じ人気の中央の馬と比べた倍率（縮めたあと）。
    """

    kind: str
    win: float
    top3: float
    runs: int
    win_factor: float
    top3_factor: float

    def note(self) -> str:
        """印の理由に足す文。"""
        return (f"{self.kind}で中央の過去走が DB に無いので、モデルの確率の代わりに、過去の{self.kind}の馬の中央での初出走 {self.runs} 走の成績で評価した"
                f"（同じ人気の中央の馬と比べて1着 {self.win_factor:.2f} 倍・3着以内 {self.top3_factor:.2f} 倍。"
                f"1着になる確率 {self.win:.1%}・3着以内に入る確率 {self.top3:.1%}）")
