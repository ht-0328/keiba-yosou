"""確認の採否の基準。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .protocol import CONFIRM_MIN_LOWER_BOUND, CONFIRM_MIN_RETURN_RATE
from .strategy_result import StrategyResult

ADOPTED = "採用"
REJECTED = "不採用"


@dataclass(frozen=True)
class ConfirmAdoptionRule:
    """確認（2025年の2区切り）で採用する基準（docs/05-round3-protocol.md。結果を見てから変えない）。

    採用 = 2区切り合計で 回収率が ``min_return_rate`` を超え、かつ 開催日単位のブートストラップの 90% の下限が
    ``min_lower_bound`` 以上。下限が届かないものは保留にせず不採用。採用が複数なら、探索の順位（渡された並び）が上の1つだけを
    最後の1回に回す（確認の結果で選ばない）。
    """

    min_return_rate: float = CONFIRM_MIN_RETURN_RATE
    min_lower_bound: float = CONFIRM_MIN_LOWER_BOUND

    def is_adopted(self, result: StrategyResult) -> bool:
        total = result.total
        if np.isnan(total.rate) or np.isnan(total.lower):
            return False
        return total.rate > self.min_return_rate and total.lower >= self.min_lower_bound

    def verdict(self, result: StrategyResult) -> str:
        return ADOPTED if self.is_adopted(result) else REJECTED

    def for_final(self, results: Sequence[StrategyResult]) -> StrategyResult | None:
        """最後の1回に回す1つ（採用のうち、探索の順位が上のもの）。採用が無ければ None。"""
        for result in results:
            if self.is_adopted(result):
                return result
        return None

    def describe(self) -> str:
        return (f"2区切り合計で回収率 {self.min_return_rate:.0%} 超、かつ 開催日単位のブートストラップの 90% の下限が "
                f"{self.min_lower_bound:.0%} 以上。届かなければ不採用（保留なし）。採用が複数なら探索の順位が上の1つだけを最後の1回へ")
