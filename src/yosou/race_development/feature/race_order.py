"""同じレースの馬の値を数える向き。"""

from __future__ import annotations

from enum import Enum


class RaceOrder(Enum):
    """``RaceOrderStatistic`` が値を数える向き。大きい値から数える（先頭率の1位など）か、小さい値から数える（上がりの速さなど）か。"""

    LARGEST_FIRST = "largest_first"
    SMALLEST_FIRST = "smallest_first"

    @property
    def ascending(self) -> bool:
        """値を小さい順に並べるか（小さい値から数えるとき）。"""
        return self is RaceOrder.SMALLEST_FIRST
