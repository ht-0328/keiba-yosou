"""買い方ごとの成績（道具「印の成績」の ``Win5StrategySummary`` に、高配当の的中の回数と、人気薄の勝ち馬を含めた割合を足したもの）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from yosou.form_aptitude_win5_tickets.settlement import STRATEGY

from 印の成績.win5_strategy_summary import Win5StrategySummary

from .hedge_day_bets import COVERED, KIND, LONGSHOT_LEGS, WIN_PAYOUT

#: 足す列。
BIG, HUGE = "100万円以上の的中", "1,000万円以上の的中"
COVERAGE = "人気薄の勝ち馬を含めた割合"
#: 高配当の線（100円あたりの払戻）。
BIG_PAYOUT, HUGE_PAYOUT = 1_000_000, 10_000_000


@dataclass(frozen=True)
class HedgeSummary:
    """``settled`` は ``HedgeDayBets`` の行。1行 = 1つの買い方。"""

    def of(self, settled: pd.DataFrame) -> pd.DataFrame:
        if settled.empty:
            return pd.DataFrame(columns=[STRATEGY, KIND, BIG, HUGE, LONGSHOT_LEGS, COVERED, COVERAGE])
        summary = Win5StrategySummary().of(settled)
        grouped = settled.groupby(STRATEGY, sort=False)
        extra = pd.DataFrame({
            KIND: grouped[KIND].first(),
            BIG: grouped[WIN_PAYOUT].apply(lambda payouts: int((payouts >= BIG_PAYOUT).sum())),
            HUGE: grouped[WIN_PAYOUT].apply(lambda payouts: int((payouts >= HUGE_PAYOUT).sum())),
            LONGSHOT_LEGS: grouped[LONGSHOT_LEGS].sum(), COVERED: grouped[COVERED].sum(),
        }).reset_index()
        merged = summary.merge(extra, on=STRATEGY, how="left")
        merged[COVERAGE] = merged[COVERED] / merged[LONGSHOT_LEGS].where(merged[LONGSHOT_LEGS] > 0)
        return merged
