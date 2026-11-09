"""集計金額（予想サイトが載せている的中の、1レースの払戻の下限）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PayoutFloor:
    """1レースの払戻（1点 100円で買った形の合計）がこの額以上の的中だけを、サイトは集計に載せている。

    ``yen`` は固定の額（例: 5,000円以上）、``per_point`` は 点数 × その額（例: 点数×500円以上）。どちらか一方を持つ。
    """

    yen: int | None = None
    per_point: int | None = None

    def __post_init__(self) -> None:
        if (self.yen is None) == (self.per_point is None):
            raise ValueError("集計金額は固定の額か 点数×額 のどちらか一方で決めてください")

    def of(self, points: int) -> int:
        """点数 ``points`` で買ったときの下限（円）。"""
        return self.yen if self.yen is not None else points * int(self.per_point)

    @property
    def label(self) -> str:
        return f"{self.yen:,}円以上" if self.yen is not None else f"点数×{self.per_point}円以上"
