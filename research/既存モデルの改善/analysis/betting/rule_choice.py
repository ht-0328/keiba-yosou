"""1つの券種について、検証期間で選んだ買い方。"""

from __future__ import annotations

from dataclasses import dataclass

from .betting_rule import BettingRule


@dataclass(frozen=True)
class RuleChoice:
    """1つの券種について、検証期間で選んだ買い方。

    - ``rule``: 回収率がいちばん高かった買い方（点数の下限を満たすものの中で）。どれも満たさなければ None。
    - ``adopted``: テスト期間に買うか（検証期間の回収率が 100% 以上だったか）。
    - ``points``・``races``・``rate``: その買い方の、検証期間の点数・買ったレース数・回収率。
    """

    rule: BettingRule | None
    adopted: bool
    points: int
    races: int
    rate: float
