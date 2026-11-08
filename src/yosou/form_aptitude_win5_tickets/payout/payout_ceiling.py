"""式の値に、自分の1票と払戻の上限を当てて、見積もりの配当にする。"""

from __future__ import annotations

import numpy as np

from .win5_rules import PAYOUT_CEILING


class PayoutCeiling:
    """設計書 06 の図2。組1つの式の値（100円あたり）を、実際に払われうる配当に直す。

    1. ほかの人の当たり票の見込み = 払戻に回るお金 ÷ 式の値（式の値で割ると、当たり票の数になる）。
    2. 自分の1票を足して分け合う: 配当 = 払戻に回るお金 ÷（ほかの人の当たり票 + 1）。ほかに当たる人がほとんどいない組ほど、
       式の値より小さくなる（払戻に回るお金を超えない）。
    3. 払戻の上限（100円あたり 6億円）で頭打ちにする。
    """

    def __init__(self, ceiling: float = PAYOUT_CEILING) -> None:
        self._ceiling = ceiling

    def apply(self, estimate: np.ndarray, money: float) -> np.ndarray:
        """組ごとの見積もりの配当（100円あたり）。``money`` は払戻に回るお金（円）。"""
        values = np.asarray(estimate, dtype=float)
        others = money / values
        shared = money / (others + 1.0)
        return np.minimum(shared, self._ceiling)
