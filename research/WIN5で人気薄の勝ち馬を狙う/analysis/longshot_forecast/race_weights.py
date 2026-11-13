"""学習の行の重み: レースごとに重みの合計をそろえる（人気薄の多い多頭数のレースに学びが偏らないように）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class RaceWeights:
    """1頭の重み = 1 ÷ そのレースの行の数 を、全体の平均が 1 になるように伸ばしたもの。"""

    def of(self, race_ids: pd.Series) -> pd.Series:
        counts = race_ids.groupby(race_ids).transform("size").astype(float)
        weights = 1.0 / counts
        return weights / weights.mean()
