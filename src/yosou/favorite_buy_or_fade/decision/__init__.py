"""判定（設計書 13）。3つの近さの点数から、1番人気を「消す」「単勝と複勝」「複勝だけ」のどれにするかを決める。

| 名前 | 仕事 |
|---|---|
| ``BuyDecision`` | 点数を比べて判定する |

判定の名前は ``bet_kinds.py``。
"""

from .bet_kinds import BET_KINDS, DECISION, FADE, PLACE_ONLY, WIN_AND_PLACE
from .buy_decision import BuyDecision

__all__ = ["BuyDecision", "BET_KINDS", "DECISION", "FADE", "WIN_AND_PLACE", "PLACE_ONLY"]
