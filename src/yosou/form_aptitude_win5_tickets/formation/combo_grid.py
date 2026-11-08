"""フォーメーションの全部の組の、当たる確率と見積もりの配当（5次元の並び）。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ComboGrid:
    """``probability[i1, i2, i3, i4, i5]`` は、1レース目の i1 番目の馬 … 5レース目の i5 番目の馬の組の当たる確率、
    ``payout`` はその組の見積もりの配当（100円あたり）。i は ``FormationValue`` に渡した各レースの馬の並びの位置。"""

    probability: np.ndarray
    payout: np.ndarray

    @property
    def expected_payout(self) -> np.ndarray:
        """組ごとの「当たる確率 × 見積もりの配当」（100円あたりの払戻の見込み）。"""
        return self.probability * self.payout
