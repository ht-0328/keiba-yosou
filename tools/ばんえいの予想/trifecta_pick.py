"""3連単の買い目の1点（1着→2着→3着の馬番、予想の組の確率、世間の見立てとのずれ）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrifectaPick:
    order: tuple[int, int, int]
    #: 予想の組の確率。
    probability: float
    #: ずれ = 予想の組の確率 ÷ 世間の見立ての組の確率。
    gap: float
    #: ずれが強い線以上か。
    strong: bool
