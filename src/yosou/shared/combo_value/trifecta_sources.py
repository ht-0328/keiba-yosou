"""3連単の全部の組に、市場の確率とモデルの Harville の確率を付ける。"""

from __future__ import annotations

import pandas as pd

from .combo_columns import horse_columns
from .horse_strength import WIN_RATIO, WIN_SHARE, TOP3_RATIO

#: 出す列。``market`` は3連単のオッズから見た組の確率、``harville`` はモデルの1着の確率から Harville の式で作った組の確率。
MARKET, HARVILLE = "market", "harville"
#: Harville の式の割り算の下限。
_MIN_LEFT = 1e-6


class TrifectaSources:
    """3連単のオッズの板（列 ``race_id``・``h1``・``h2``・``h3``・``odds``）と、馬ごとの見立て（``HorseStrength.of``）から、3連単の組ごとに2つの確率を出す。

    - ``market``: オッズの逆数を、レースの全部の組（オッズのある組）で合計 1 にそろえた値。
    - ``harville``: 1着の確率（``win_share``）から、i→j→k = w_i × w_j ÷（1 − w_i）× w_k ÷（1 − w_i − w_j）。
      見立ての無い馬（比の欠損した馬）を含む組を落としてから、レースで合計 1 にそろえる。
    戻り値は1行 = 3連単の1組。列は ``race_id``・``h1``〜``h3``・``market``・``harville``。
    """

    def of(self, board: pd.DataFrame, strength: pd.DataFrame) -> pd.DataFrame:
        rows = board[board["odds"] > 0].copy()
        rows["race_id"] = rows["race_id"].astype(str)
        inverse = 1.0 / rows["odds"]
        rows[MARKET] = inverse / inverse.groupby(rows["race_id"]).transform("sum")
        rows = self._with_horses(rows, strength)
        w1, w2, w3 = rows["w1"], rows["w2"], rows["w3"]
        harville = w1 * w2 / (1 - w1).clip(lower=_MIN_LEFT) * w3 / (1 - w1 - w2).clip(lower=_MIN_LEFT)
        rows[HARVILLE] = harville / harville.groupby(rows["race_id"]).transform("sum")
        return rows[["race_id", *horse_columns(3), MARKET, HARVILLE]].reset_index(drop=True)

    def _with_horses(self, rows: pd.DataFrame, strength: pd.DataFrame) -> pd.DataFrame:
        """組の3頭の 1着の確率（``w1``〜``w3``）を付け、1頭目の1着の比・2・3頭目の3着以内の比が無い組を落とす。"""
        table = strength.set_index(["race_id", "horse_no"])
        for at, name in enumerate(horse_columns(3), start=1):
            found = table.reindex(pd.MultiIndex.from_arrays([rows["race_id"], rows[name].astype(int)]))
            rows[f"w{at}"] = found[WIN_SHARE].to_numpy()
            rows[f"ratio{at}"] = (found[WIN_RATIO] if at == 1 else found[TOP3_RATIO]).to_numpy()
        return rows.dropna(subset=["w1", "w2", "w3", "ratio1", "ratio2", "ratio3"])
