"""買い目の表からの、回収率のまとめ。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from 既存モデルの改善.analysis.scores import BootstrapInterval, ConservativeRate

from . import columns as c


@dataclass(frozen=True)
class TicketSummary:
    """買い目の表（``CandidatePicker`` の列）からのまとめ。

    - ``points``・``races``・``days``: 点数・買ったレース数・買った開催日数。
    - ``stake_yen``・``payout_yen``・``hit_points``: 賭け金・払戻の合計（円）と、当たった点数。
    - ``lower``・``upper``: 回収率の 90% の幅（開催日を単位にしたブートストラップ。``BootstrapInterval``）。
    - ``conservative``: 控えめな見積もり（回収率 − 1.645 × 開催日単位のばらつき。``ConservativeRate``）。
    回収率 = 払戻 ÷ 賭け金（1.0 で元返し）。買っていなければ NaN。
    """

    points: int
    races: int
    days: int
    stake_yen: int
    payout_yen: int
    hit_points: int
    lower: float
    upper: float
    conservative: float

    @classmethod
    def of(cls, tickets: pd.DataFrame, interval: BootstrapInterval | None = None) -> TicketSummary:
        if tickets.empty:
            return cls(0, 0, 0, 0, 0, 0, np.nan, np.nan, np.nan)
        day, stake, payout = tickets[c.RACE_DATE], tickets[c.STAKE_YEN].astype(float), tickets[c.PAYOUT_YEN].astype(float)
        lower, upper = (interval or BootstrapInterval()).of(day, stake, payout)
        return cls(
            points=len(tickets), races=int(tickets[c.RACE_ID].nunique()), days=int(day.nunique()),
            stake_yen=int(stake.sum()), payout_yen=int(payout.sum()), hit_points=int((payout > 0).sum()),
            lower=lower, upper=upper, conservative=ConservativeRate().of(day, stake, payout),
        )

    @property
    def rate(self) -> float:
        """回収率。買っていなければ NaN。"""
        return self.payout_yen / self.stake_yen if self.stake_yen else float("nan")

    @property
    def hit_rate(self) -> float:
        """点の的中率。買っていなければ NaN。"""
        return self.hit_points / self.points if self.points else float("nan")
