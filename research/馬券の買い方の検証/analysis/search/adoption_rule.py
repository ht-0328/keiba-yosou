"""採否の基準。"""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from dataclasses import dataclass

from ..summary import ReturnSummary

ADOPTED = "候補"
NOT_ADOPTED = ""


@dataclass(frozen=True)
class AdoptionRule:
    """探索期間で戦略を候補にする基準（docs/03-protocol.md。結果を見てから変えない）。

    回収率が ``min_return_rate`` 以上、かつ 買ったレース数が ``min_races`` 以上か点数が ``min_points`` 以上、
    かつ 最大の1レースの払戻を除いた回収率が ``min_return_rate_without_max`` 以上、
    かつ 月別の回収率の中央値が ``min_monthly_median`` 以上（2回目の検証で足した。数か月の大当たり頼みを弾く）。
    """

    min_return_rate: float = 1.0
    min_races: int = 100
    min_points: int = 300
    min_return_rate_without_max: float = 0.9
    min_monthly_median: float = 0.9

    def is_adopted(self, summary: ReturnSummary, monthly_rates: Sequence[float] = ()) -> bool:
        if summary.return_rate is None or summary.return_rate < self.min_return_rate:
            return False
        if summary.bet_races < self.min_races and summary.points < self.min_points:
            return False
        if (summary.return_rate_without_max or 0.0) < self.min_return_rate_without_max:
            return False
        return not monthly_rates or statistics.median(monthly_rates) >= self.min_monthly_median

    def verdict(self, summary: ReturnSummary, monthly_rates: Sequence[float] = ()) -> str:
        return ADOPTED if self.is_adopted(summary, monthly_rates) else NOT_ADOPTED

    def describe(self) -> str:
        return (f"回収率 {self.min_return_rate:.0%} 以上、買ったレース {self.min_races} 以上（または点数 {self.min_points} 以上）、"
                f"最大の1レースを除く回収率 {self.min_return_rate_without_max:.0%} 以上、"
                f"月別の回収率の中央値 {self.min_monthly_median:.0%} 以上")
