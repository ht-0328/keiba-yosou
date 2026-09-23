"""Stern のべき乗を推定するための、1〜3着がそろったレースの並びを作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd


class RaceFinishSample:
    """レースごとに（勝率, 1着の位置, 2着の位置, 3着の位置）の並びを作る。

    ``SternFitter`` は「観測した 1着 → 2着 → 3着 の並びが、いちばん起きやすくなる λ・μ」を探す。
    そのために、レース単位で「誰が何着だったか」を、行の位置で渡す必要がある。

    1〜3着のどれかが欠けているレース（競走中止などで着順が付かなかった場合）は使わない。
    """

    def __init__(self, probability_column: str) -> None:
        self._probability_column = probability_column

    def build(self, table: pd.DataFrame, limit: int | None = None,
              seed: int = 20260923) -> list[tuple[np.ndarray, int, int, int]]:
        """``limit`` を渡すと、その数だけ無作為に選ぶ（推定は数千レースあれば足りる）。"""
        races = []
        for _, group in table.groupby("rid", sort=False):
            finish = group["finish"].to_numpy()
            positions = [np.flatnonzero(finish == rank) for rank in (1, 2, 3)]
            if any(len(found) != 1 for found in positions):
                continue
            probability = group[self._probability_column].to_numpy()
            races.append((probability / probability.sum(),
                          int(positions[0][0]), int(positions[1][0]), int(positions[2][0])))
        if limit is None or len(races) <= limit:
            return races
        chosen = np.random.default_rng(seed).choice(len(races), size=limit, replace=False)
        return [races[index] for index in chosen]
