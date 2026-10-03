"""トリガミになる買い目を外す。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 今週の予想.mark_tickets import ODDS, RULE

#: 外した理由の列（空なら買う）。
DROPPED = "dropped"
NO_ODDS, TORIGAMI = "オッズ無し", "トリガミ"


class TorigamiFilter:
    """1レース・1買い方の買い目から、どれが当たっても買い方の投資より少なくしか戻らない買い目（トリガミ）を外す
    （設計書「買うレースと買い目を決める」08 の 2。研究「既存モデルの改善」の ``StakeAllocator`` と同じ決まり）。

    1点の額は買い方の中で均等なので、払戻がいちばん少ない買い目の「オッズ × 1点」が「1点 × 点数」以下なら、その買い目を外して
    数え直す。全部の買い目が投資より多く戻るまで繰り返す。確定オッズの無い組（無投票・取消）は買えないので、先に外す。
    複勝・ワイドのオッズは最低オッズ（いちばん少ない払戻で確かめる）。
    列 ``dropped`` に外した理由を入れる（空なら買う）。
    """

    def apply(self, tickets: pd.DataFrame) -> pd.DataFrame:
        table = tickets.copy()
        table[DROPPED] = np.where(table[ODDS].isna(), NO_ODDS, "")
        for _, group in table[table[DROPPED] == ""].groupby(["race_id", RULE], sort=False):
            for row in self._torigami_rows(group[ODDS]):
                table.loc[row, DROPPED] = TORIGAMI
        return table

    def _torigami_rows(self, odds: pd.Series) -> list:
        """外す行の index。"""
        kept = odds.sort_values(ascending=False)
        dropped = []
        while len(kept) and kept.iloc[-1] <= len(kept):
            dropped.append(kept.index[-1])
            kept = kept.iloc[:-1]
        return dropped
