"""最後の1回（2026年）の判定。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .protocol import FINAL_MIN_RETURN_RATE
from .strategy_result import StrategyResult

PROPOSE = "提案へ"
DROP = "提案しない"


@dataclass(frozen=True)
class FinalRule:
    """最後の1回で、採用した1つを提案に進めるかの基準（docs/05-round3-protocol.md。結果を見てから変えない）。

    回収率が ``min_return_rate`` を割らなければ提案へ。2026年を見て線や軸を直さない。
    """

    min_return_rate: float = FINAL_MIN_RETURN_RATE

    def passes(self, result: StrategyResult) -> bool:
        rate = result.total.rate
        return not np.isnan(rate) and rate >= self.min_return_rate

    def verdict(self, result: StrategyResult) -> str:
        return PROPOSE if self.passes(result) else DROP

    def describe(self) -> str:
        return f"2026年の回収率が {self.min_return_rate:.0%} を割らなければ提案へ。ここを見て線や軸を直さない"
