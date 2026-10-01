"""買った馬券の、年ごとの回収率と幅の表。"""

from __future__ import annotations

import pandas as pd

from .payback import Payback
from .payback_interval import PaybackInterval

#: 合計の行の「年」の値。
TOTAL_LABEL = "合計"


class YearlyPaybackTable:
    """1点 100円で買った馬券（1行 = 1点）から、年ごとの買い目・的中率・回収率・90% の幅の表を作る。最後の行は合計。

    入力の列: year・day・place_payout（100円あたりの払戻。外れは 0）。
    幅は、開催日を丸ごと取り直すブートストラップ（``PaybackInterval``）。``backtest.py`` の「検証の結果」と、
    確率の出どころを替えた比べ（``probability_source``）で、同じ表を書くために1か所にまとめた。
    """

    def __init__(self, interval: PaybackInterval | None = None) -> None:
        self._interval = interval or PaybackInterval()

    def build(self, bought: pd.DataFrame) -> pd.DataFrame:
        rows = [self.row(int(year), group) for year, group in bought.groupby("year")]
        rows.append(self.row(TOTAL_LABEL, bought))
        return pd.DataFrame(rows)

    def row(self, label: object, group: pd.DataFrame) -> dict[str, object]:
        """1行ぶん（年か合計）。"""
        payback = Payback(group["place_payout"])
        low, high = self._interval.of(group["day"], group["place_payout"])
        return {"年": label, "買い目": payback.bet_count, "的中率": round(payback.hit_rate, 3),
                "回収率": round(payback.rate, 1), "90%の下限": round(low, 1), "90%の上限": round(high, 1)}
