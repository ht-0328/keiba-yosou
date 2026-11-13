"""段階の予算（判断用・少なく買う日・多く買う日の予算と、多く買う日の線）を表す値。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .day_decision import DayDecision


@dataclass(frozen=True)
class BudgetTiers:
    """設計書 15 の 13。``judge`` は判断用の買い目の予算（点。この買い目の日の期待値で買うか見送りかを決める）、``small`` は少なく買う日の
    予算（点）、``large`` は多く買う日の予算（点）、``favorite_line`` は多く買う日の線（本命の確率の積がこの値以上なら多く買う）。
    既定の値は ``buying_defaults.py``。"""

    judge: int
    small: int
    large: int
    favorite_line: float

    def __post_init__(self) -> None:
        if min(self.judge, self.small, self.large) < 1:
            raise ValueError(f"予算は 1点以上にしてください: 判断用 {self.judge}・少なく {self.small}・多く {self.large}")
        if self.small > self.large:
            raise ValueError(f"少なく買う日の予算は多く買う日の予算以下にしてください: {self.small} > {self.large}")

    @property
    def budgets(self) -> tuple[int, ...]:
        """買い目を組む予算（判断用・少なく・多く。重なりを除いて小さい順）。"""
        return tuple(sorted({self.judge, self.small, self.large}))

    def budget_for(self, decision: DayDecision) -> int:
        """その判断で買う買い目の予算（多く買う日は ``large``、少なく買う日は ``small``。見送りの日も ``small`` の買い目を参考に出す）。"""
        return self.large if decision is DayDecision.BUY_LARGE else self.small

    def to_dict(self) -> dict[str, Any]:
        return {"判断用の予算": self.judge, "少なく買う日の予算": self.small, "多く買う日の予算": self.large, "多く買う日の線": self.favorite_line}
