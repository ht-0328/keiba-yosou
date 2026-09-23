"""回収率（払戻の合計 ÷ 賭けた金の合計）。"""

from __future__ import annotations

import pandas as pd

#: 1点あたりの賭け金（円）。
STAKE = 100.0


class Payback:
    """買った馬券の払戻から回収率を出す。

    レースごとの回収率を平均するのではなく、期間全体の「払戻の合計 ÷ 賭けた金の合計」で出す。
    平均を取ると、買い目が1点だけのレースと20点のレースが同じ重みになってしまう。
    """

    def __init__(self, payout: pd.Series) -> None:
        self._payout = payout

    @property
    def bet_count(self) -> int:
        return len(self._payout)

    @property
    def rate(self) -> float:
        """回収率（%）。買い目が無ければ NaN。"""
        if self.bet_count == 0:
            return float("nan")
        return float(self._payout.sum() / (STAKE * self.bet_count) * 100)

    @property
    def hit_rate(self) -> float:
        """的中率。"""
        if self.bet_count == 0:
            return float("nan")
        return float((self._payout > 0).mean())
