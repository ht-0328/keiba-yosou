"""判断用の買い目の日の期待値と本命の確率の積から、買う（多く）・買う（少なく）・見送り を決める。"""

from __future__ import annotations

from .day_decision import DayDecision


class BudgetTierJudge:
    """設計書 06 の図3 の最後（15 の 13）。判断用の買い目の日の期待値が買う日の線未満なら「見送り」。線以上なら買う日で、
    本命の確率の積が多く買う日の線以上なら「買う（多く）」、未満なら「買う（少なく）」。"""

    def judge(self, expected_value: float, line: float, favorite_product: float, favorite_line: float) -> DayDecision:
        """``expected_value`` は判断用の買い目の日の期待値、``line`` は買う日の線、``favorite_product`` は本命の確率の積、
        ``favorite_line`` は多く買う日の線。"""
        if expected_value < line:
            return DayDecision.SKIP
        return DayDecision.BUY_LARGE if favorite_product >= favorite_line else DayDecision.BUY_SMALL
