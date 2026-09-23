"""回収率のばらつきの幅（ブートストラップ信頼区間）。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .payback import STAKE


class PaybackInterval:
    """開催日を単位に取り直して、回収率の幅を出す。

    買い目を1つずつ独立に取り直すと、幅が実際より狭く出る。同じ日・同じレースの買い目は
    結果が連動する（1頭が3着以内なら、ほかの馬は入りにくい）ためである。
    そこで、開催日ごと丸ごと取り直す。

    幅の下限が 100% を超えて初めて「回収率が 100% を超えた」と言える。
    点の回収率が 100% を超えていても、下限が 100% を割るなら証拠としては足りない。
    """

    def __init__(self, rounds: int = 2000, confidence: float = 0.90, seed: int = 20260923) -> None:
        self._rounds = rounds
        self._confidence = confidence
        self._random = np.random.default_rng(seed)

    def of(self, day: pd.Series, payout: pd.Series) -> tuple[float, float]:
        """（下限, 上限）を % で返す。開催日が無ければ NaN。"""
        by_day = pd.DataFrame({"day": day, "payout": payout}).groupby("day").agg(
            payout=("payout", "sum"), bets=("payout", "size"))
        if len(by_day) == 0:
            return float("nan"), float("nan")
        values = by_day[["payout", "bets"]].to_numpy()
        draws = self._random.integers(0, len(values), size=(self._rounds, len(values)))
        totals = values[draws].sum(axis=1)
        rates = totals[:, 0] / (STAKE * totals[:, 1]) * 100
        tail = (1.0 - self._confidence) / 2 * 100
        return float(np.percentile(rates, tail)), float(np.percentile(rates, 100 - tail))
