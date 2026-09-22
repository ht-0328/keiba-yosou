"""障害レースと、出走しなかった馬の行を除く。"""

from __future__ import annotations

import pandas as pd

#: 障害レースの芝ダ。どの予想も学習データに入れない。
JUMP = "障害"


class FlatRunnerFilter:
    """平地を走った馬の行だけにする（設計書 06 の図1 の、はじめの2つの問い）。

    どの予想でも同じ決まりなので、行を選ぶクラス（``SampleSelector``）から使う。
    """

    def apply(self, entries: pd.DataFrame) -> pd.DataFrame:
        """障害レースと、出走しなかった馬（出走取消・発走除外・競走除外）を除いた行。"""
        is_flat = entries["surface"] != JUMP
        has_run = entries["ran"].eq(True)
        return entries[is_flat & has_run]
