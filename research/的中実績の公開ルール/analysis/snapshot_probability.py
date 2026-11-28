"""確定オッズで出した1着の確率を、締め切り前のオッズの時点の確率に近づける。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: ロジットを取るときの確率の端。
_EDGE = 1e-4


class SnapshotProbability:
    """1着のモデルは、オッズから見た勝率のロジットを出発点（基準）にして、そこからの上げ下げを学んでいる（``WinBaseline``）。
    過去の予測は確定オッズの基準で出ているので、基準だけを締め切り前のオッズのものに差し替えて、その時点の確率の近似にする:
    ``logit(その時点の確率) = logit(確定の確率) − logit(確定のオッズから見た勝率) + logit(その時点のオッズから見た勝率)``。レースの中で合計 1 にそろえる。

    材料にしている単勝オッズそのもの（木の分かれ目）の違いは直らないので、近似である。
    """

    def of(self, frame: pd.DataFrame) -> pd.Series:
        """``frame`` の列は ``race_id``・``p``（確定のときの1着の確率）・``odds``（確定の単勝オッズ）・``snapshot_odds``（その時点の単勝オッズ）。"""
        final_market = _market(frame["race_id"], frame["odds"])
        snapshot_market = _market(frame["race_id"], frame["snapshot_odds"])
        shifted = _sigmoid(_logit(frame["p"]) - _logit(final_market) + _logit(snapshot_market))
        return shifted / shifted.groupby(frame["race_id"]).transform("sum")


def _market(race_id: pd.Series, odds: pd.Series) -> pd.Series:
    """オッズから見た勝率（単勝オッズの逆数を、レースの中で合計 1 にそろえた値）。"""
    inverse = 1.0 / odds
    return inverse / inverse.groupby(race_id).transform("sum")


def _logit(p: pd.Series) -> pd.Series:
    clipped = p.clip(_EDGE, 1 - _EDGE)
    return np.log(clipped / (1 - clipped))


def _sigmoid(x: pd.Series) -> pd.Series:
    return 1.0 / (1.0 + np.exp(-x))
