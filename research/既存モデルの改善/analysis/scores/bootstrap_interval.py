"""回収率の推定幅（開催日を単位にしたブートストラップ）。"""

from __future__ import annotations

import numpy as np
import pandas as pd


class BootstrapInterval:
    """回収率の推定幅を、開催日を単位に選び直して（ブートストラップ）出す。

    同じ日のレースは馬場や天気が共通なので、1点ずつではなく開催日ごとにまとめて選び直す。
    例: 90% の幅が 95%〜118% なら、「たまたまの当たり外れを考えると、回収率はおおよそこの範囲」という意味。
    """

    def __init__(self, rounds: int = 2000, confidence: float = 0.90, seed: int = 20260924) -> None:
        self._rounds = rounds
        self._confidence = confidence
        self._seed = seed

    def of(self, day: pd.Series, stake: pd.Series, payout: pd.Series) -> tuple[float, float]:
        """（下限, 上限）。回収率（払戻 ÷ 賭け金）の値で返す。買った点が無ければ（NaN, NaN）。"""
        by_day = pd.DataFrame({"day": day.to_numpy(), "stake": stake.to_numpy(), "payout": payout.to_numpy()})
        totals = by_day.groupby("day")[["stake", "payout"]].sum()
        if totals["stake"].sum() <= 0:
            return float("nan"), float("nan")
        rng = np.random.default_rng(self._seed)
        picks = rng.integers(0, len(totals), size=(self._rounds, len(totals)))
        stakes = totals["stake"].to_numpy()[picks].sum(axis=1)
        payouts = totals["payout"].to_numpy()[picks].sum(axis=1)
        rates = payouts / np.where(stakes > 0, stakes, np.nan)
        tail = (1.0 - self._confidence) / 2.0
        return float(np.nanquantile(rates, tail)), float(np.nanquantile(rates, 1.0 - tail))
