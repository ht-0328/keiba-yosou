"""勝つ力を 3着以内の確率に合わせて解く: Harville の式で出る 3着以内率が、全頭の予想の 3着以内の確率（市場より当たる方の予想）と一致する勝つ力を、レースごとに繰り返しで求める。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from yosou.shared.feature.odds import HarvillePlaces
from yosou.shared.feature.odds.column_names import TOP3_RATE

_FLOOR = 1e-6


@dataclass(frozen=True)
class Top3FittedStrength:
    """``fit(race_ids, start, top3)`` は、``start``（1着の確率など）から始めて、Harville の 3着以内率が ``top3`` に近づくよう
    ``strength ← strength × (top3 ÷ 3着以内率) ^ step`` をレース内で合計 1 にそろえながら繰り返した勝つ力を返す。"""

    iterations: int = 60
    step: float = 0.8

    def fit(self, race_ids: pd.Series, start: pd.Series, top3: pd.Series) -> pd.Series:
        strength = start.clip(lower=_FLOOR).astype(float)
        target = top3.clip(lower=_FLOOR, upper=1.0 - _FLOOR)
        for _ in range(self.iterations):
            strength = strength / strength.groupby(race_ids).transform("sum")
            current = HarvillePlaces().places(race_ids, strength)[TOP3_RATE].clip(lower=_FLOOR)
            strength = strength * np.power(target / current, self.step)
        return strength / strength.groupby(race_ids).transform("sum")
