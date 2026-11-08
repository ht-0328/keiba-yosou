"""日の期待値と買う日の線から、買うかどうかを決める。"""

from __future__ import annotations

from .day_decision import DayDecision


class DayBuyJudge:
    """設計書 06 の図3 の最後。日の期待値が買う日の線以上なら「買う」、未満なら「見送り」。"""

    def judge(self, expected_value: float, line: float) -> DayDecision:
        return DayDecision.BUY if expected_value >= line else DayDecision.SKIP
