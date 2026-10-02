"""回収率の控えめな見積もり（運が悪い方に転んだときの値）。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 片側 5% の点（90% の幅の下の端）。
_Z = 1.645


class ConservativeRate:
    """回収率の控えめな見積もり = 回収率 − 1.645 × 回収率のばらつき（開催日を単位にしたもの）。

    同じ日のレースは馬場や天気が共通なので、開催日ごとにまとめてばらつきを見る。ブートストラップの 90% の幅の
    下の端とほぼ同じ意味で、何百通りの買い方を比べるときに速く出せる（比の推定量の分散の近似）。
    例: 回収率 120% でも当たりが数回だけならばらつきが大きく、控えめな見積もりは 60% のように低くなる。
    """

    def of(self, day: pd.Series, stake: pd.Series, payout: pd.Series) -> float:
        """控えめな見積もり（回収率の値）。買った点が無いか、開催日が2日に満たなければ NaN。"""
        totals = pd.DataFrame({"day": day.to_numpy(), "stake": stake.to_numpy(), "payout": payout.to_numpy()}) \
            .groupby("day")[["stake", "payout"]].sum()
        stake_total = float(totals["stake"].sum())
        if stake_total <= 0 or len(totals) < 2:
            return float("nan")
        rate = float(totals["payout"].sum()) / stake_total
        residual = totals["payout"].to_numpy() - rate * totals["stake"].to_numpy()
        variance = len(totals) / (len(totals) - 1) * float(np.sum(residual ** 2)) / stake_total ** 2
        return rate - _Z * float(np.sqrt(variance))
