"""3連単の板から見た、馬ごとの勝率。"""

from __future__ import annotations

import pandas as pd

from ..feature.column_names import COMBO, HORSE_NO, ODDS, RACE_ID

#: 出す列。3連単の板から見た勝率。
POOL_WIN = "pool_win"


class TrifectaPoolWin:
    """3連単の板（列 ``race_id``・``combo``・``odds``）から、馬ごとの「3連単の市場が見た勝率」を出す。

    組ごとの市場の確率（1 ÷ オッズ をレースで合計 1 にそろえた値）を、1着の馬ごとに足す。オッズの無い組（0 以下・欠損）は数えない。
    例: 4番が1着の組の確率の合計が 0.25 なら、4番の値は 0.25。列は ``race_id``・``horse_no``・``pool_win``。
    """

    def of(self, trifecta_board: pd.DataFrame) -> pd.DataFrame:
        rows = trifecta_board[trifecta_board[ODDS] > 0]
        race_id = rows[RACE_ID].astype(str)
        inverse = 1.0 / rows[ODDS].astype(float)
        share = inverse / inverse.groupby(race_id).transform("sum")
        first_horse = rows[COMBO].astype(str).str[:2].astype(int)
        table = pd.DataFrame({RACE_ID: race_id, HORSE_NO: first_horse, POOL_WIN: share})
        return table.groupby([RACE_ID, HORSE_NO], as_index=False, sort=False)[POOL_WIN].sum()
