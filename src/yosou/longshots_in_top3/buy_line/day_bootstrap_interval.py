"""回収率の推定幅（開催日を単位にしたブートストラップ）。"""

from __future__ import annotations

import numpy as np
import pandas as pd


class DayBootstrapInterval:
    """回収率の推定幅を、開催日を単位に選び直して（ブートストラップ）出す（研究「既存モデルの改善」と同じ出し方）。

    同じ日のレースは馬場や天気が共通なので、1点ずつではなく開催日ごとにまとめて選び直す。
    例: 90% の幅が 95%〜118% なら、「たまたまの当たり外れを考えると、回収率はおおよそこの範囲」という意味。
    下限が 100% 以上なら、偶然の幅を考えても 100% を超えていると言える。
    """

    def __init__(self, rounds: int = 2000, confidence: float = 0.90, seed: int = 20260924) -> None:
        self._rounds = rounds
        self._confidence = confidence
        self._seed = seed

    def of(self, day: pd.Series, payout: pd.Series, stake: float = 100.0) -> tuple[float, float]:
        """（下限, 上限）。1点 ``stake`` 円で買ったときの回収率（払戻 ÷ 賭け金）の値。買った点が無ければ（NaN, NaN）。"""
        paid = pd.to_numeric(payout, errors="coerce").fillna(0.0).to_numpy(dtype="float64")
        by_day = pd.DataFrame({"day": day.to_numpy(), "stake": stake, "payout": paid})
        totals = by_day.groupby("day")[["stake", "payout"]].sum()
        if totals.empty:
            return float("nan"), float("nan")
        rng = np.random.default_rng(self._seed)
        picks = rng.integers(0, len(totals), size=(self._rounds, len(totals)))
        stakes = totals["stake"].to_numpy()[picks].sum(axis=1)
        payouts = totals["payout"].to_numpy()[picks].sum(axis=1)
        rates = payouts / stakes
        tail = (1.0 - self._confidence) / 2.0
        return float(np.quantile(rates, tail)), float(np.quantile(rates, 1.0 - tail))
