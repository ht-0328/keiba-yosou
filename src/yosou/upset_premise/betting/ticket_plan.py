"""買い方の決まり。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from .race_horses import RaceHorses


class TicketPlan(Protocol):
    """買い方の決まり（インターフェース）。守るクラスは ``ObiStakePlan``（甲・丙）と ``FormationPlan``（乙）。

    ``name`` は表に出す名前、``ordered`` は3連単なら真・3連複なら偽（組の馬番の並べ方とオッズの引き方が変わる）。
    ``tickets`` は、1レースの出走馬ごとの予想と、組 → オッズ から、（組, 掛け金（円））の並びを返す。
    """

    name: str
    ordered: bool

    def tickets(self, horses: RaceHorses, odds: Mapping[tuple[int, ...], float]) -> list[tuple[tuple[int, ...], int]]:
        ...
