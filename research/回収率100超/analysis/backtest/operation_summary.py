"""買った馬券から、実際に運用したときの規模と、負けが続いたときの深さを数える。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .payback import STAKE


@dataclass(frozen=True)
class OperationTotals:
    """期間全体の、負けの深さ。金額は円（1点 100円）。"""

    longest_losing_streak: int
    max_drawdown: float
    max_bets_per_race: int


class OperationSummary:
    """1点 100円で買った馬券（1行 = 1点）の、年ごとの規模と、期間全体の負けの深さ。

    入力の列: year・day・rid・payout（100円あたりの払戻。外れは 0）。
    連敗と落ち込みは、開催日・レースの順に並べて数える（同じレースの中の順は問わない）。
    """

    def yearly(self, bought: pd.DataFrame) -> pd.DataFrame:
        """年ごとの、買い目・買った日・1日の点数・投資・払戻・損益。"""
        grouped = bought.groupby("year")
        table = pd.DataFrame({
            "買い目": grouped.size(),
            "買った日": grouped["day"].nunique(),
            "投資": grouped.size() * STAKE,
            "払戻": grouped["payout"].sum(),
        })
        table["1日の点数"] = (table["買い目"] / table["買った日"]).round(1)
        table["損益"] = table["払戻"] - table["投資"]
        return table.reset_index().rename(columns={"year": "年"})

    def totals(self, bought: pd.DataFrame) -> OperationTotals:
        ordered = bought.sort_values(["day", "rid"])
        profit = ordered["payout"].to_numpy() - STAKE
        cumulative = profit.cumsum()
        peak = pd.Series(cumulative).cummax().clip(lower=0)
        return OperationTotals(
            longest_losing_streak=self._longest_run(ordered["payout"].to_numpy() == 0),
            max_drawdown=float((peak - cumulative).max()) if len(cumulative) else 0.0,
            max_bets_per_race=int(bought.groupby("rid").size().max()) if len(bought) else 0,
        )

    @staticmethod
    def _longest_run(missed) -> int:
        longest = current = 0
        for is_miss in missed:
            current = current + 1 if is_miss else 0
            longest = max(longest, current)
        return longest
