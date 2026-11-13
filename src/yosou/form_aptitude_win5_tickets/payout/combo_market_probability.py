"""過去の WIN5 の当たり組の、市場の組の確率。"""

from __future__ import annotations

import math
from collections.abc import Sequence

import pandas as pd


class ComboMarketProbability:
    """当たり組の5頭の確定単勝オッズと、各対象レースの全頭の単勝オッズの逆数の合計から、市場の組の確率を出す。

    1頭のオッズから見た勝率は「単勝オッズの逆数 ÷ そのレースの全頭の逆数の合計」（共通の ``MarketWinProbability`` と同じ決まり）。
    組の確率は5頭のかけ算。オッズの欠けている頭があれば欠損値（式を作るのに使わない）。
    """

    def of_winners(self, winner_odds: pd.Series, inverse_sums: pd.Series) -> pd.Series:
        """行ごとの市場の組の確率。``winner_odds``・``inverse_sums`` は行ごとに5つの値のリスト。index は ``winner_odds`` と同じ。"""
        values = [self._combo(odds, sums) for odds, sums in zip(winner_odds, inverse_sums, strict=True)]
        return pd.Series(values, index=winner_odds.index, dtype=float)

    def _combo(self, odds: Sequence[float | None], sums: Sequence[float | None]) -> float:
        shares = [self._share(each_odds, each_sum) for each_odds, each_sum in zip(odds, sums, strict=True)]
        if any(math.isnan(share) for share in shares):
            return math.nan
        return math.prod(shares)

    def _share(self, odds: float | None, inverse_sum: float | None) -> float:
        """1頭のオッズから見た勝率。値が無い・0 以下なら NaN。"""
        if odds is None or inverse_sum is None or pd.isna(odds) or pd.isna(inverse_sum) or odds <= 0 or inverse_sum <= 0:
            return math.nan
        return (1.0 / odds) / inverse_sum
