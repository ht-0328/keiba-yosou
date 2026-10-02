"""単勝オッズから見た勝率。"""

from __future__ import annotations

import pandas as pd

from ..value_types import as_numbers


class MarketWinProbability:
    """単勝オッズの逆数を、レース内で合計 1 にそろえた勝率（オッズから見た勝率）を出す。

    単勝オッズには JRA の取り分（控除率）が入っているので、逆数をそのまま足すと 1 を超える。
    レース内で合計 1 にそろえると、市場がその馬に付けた勝率になる。オッズが無い馬（木曜・無投票）は欠損値で、
    その馬を除いた馬どうしでそろえる。
    """

    def of(self, race_ids: pd.Series, win_odds: pd.Series) -> pd.Series:
        """行ごとの勝率。index は ``win_odds`` と同じ。"""
        odds = as_numbers(win_odds)
        inverse = (1.0 / odds).where(odds > 0)
        return inverse / inverse.groupby(race_ids).transform("sum")
