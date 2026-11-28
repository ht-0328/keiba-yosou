"""馬連のオッズの板から、馬ごとの「馬連から見た2着以内率」を出す。"""

from __future__ import annotations

import pandas as pd

#: 出す列。
QUINELLA_TOP2 = "quinella_top2"
#: 組番の中の馬番の桁数。
_DIGITS = 2


class QuinellaTop2:
    """馬連の板（1行 = 1組。列 ``race_id``・``combo``（馬番を2桁ずつ）・``odds``）から、オッズの逆数をレースで合計 1 にそろえ、
    組に入る馬ごとに足した率（レースで合計 2）を出す。列は ``race_id``・``horse_no``・``quinella_top2``。オッズの無い組は使わない。

    例: 3頭のレースで 1-2 が 2倍・1-3 と 2-3 が 4倍なら、逆数 0.5・0.25・0.25（合計 1）で、1番 0.75・2番 0.75・3番 0.5。
    """

    def of(self, board: pd.DataFrame) -> pd.DataFrame:
        priced = board[pd.to_numeric(board["odds"], errors="coerce") > 0]
        race = priced["race_id"].astype(str)
        inverse = 1.0 / priced["odds"].astype(float)
        share = inverse / inverse.groupby(race).transform("sum")
        combo = priced["combo"].astype(str)
        sides = [pd.DataFrame({"race_id": race, "horse_no": combo.str[start:start + _DIGITS].astype(int), QUINELLA_TOP2: share})
                 for start in (0, _DIGITS)]
        return pd.concat(sides).groupby(["race_id", "horse_no"], as_index=False)[QUINELLA_TOP2].sum()
