"""賭け金が買い目ごとに違うときの、回収率とそのばらつきの幅。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PaybackSummary:
    """買った馬券の成績。回収率と幅は %。"""

    bets: int
    hits: int
    stake: float
    returned: float
    rate: float
    low: float
    high: float


class StakedPayback:
    """買い目ごとの賭け金（円）と、100円あたりの払戻から、回収率と 90% の幅を出す。

    ``Payback``・``PaybackInterval`` は1点 100円の均等を前提にしている。印のルールの買い方は
    券種・買い目で賭け金が違う（例: 3連複 0.3単位・ワイド 1単位）ので、金額で数える。
    幅は、``PaybackInterval`` と同じく開催日を丸ごと取り直すブートストラップで出す。
    """

    def __init__(self, rounds: int = 2000, confidence: float = 0.90, seed: int = 20260927) -> None:
        self._rounds = rounds
        self._confidence = confidence
        self._seed = seed

    def summarize(self, day: pd.Series, stake: pd.Series, payout_per_100: pd.Series) -> PaybackSummary:
        returned = payout_per_100 * stake / 100.0
        if len(stake) == 0:
            return PaybackSummary(0, 0, 0.0, 0.0, float("nan"), float("nan"), float("nan"))
        by_day = pd.DataFrame({"day": day.to_numpy(), "stake": stake.to_numpy(),
                               "returned": returned.to_numpy()}).groupby("day")[["stake", "returned"]].sum()
        low, high = self._interval(by_day.to_numpy())
        rate = float(returned.sum() / stake.sum() * 100)
        return PaybackSummary(len(stake), int((payout_per_100 > 0).sum()), float(stake.sum()),
                              float(returned.sum()), rate, low, high)

    def _interval(self, values: np.ndarray) -> tuple[float, float]:
        draws = np.random.default_rng(self._seed).integers(0, len(values), size=(self._rounds, len(values)))
        totals = values[draws].sum(axis=1)
        rates = totals[:, 1] / totals[:, 0] * 100
        tail = (1.0 - self._confidence) / 2 * 100
        return float(np.percentile(rates, tail)), float(np.percentile(rates, 100 - tail))
