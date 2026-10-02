"""金額を上げるときの上限（自分の投票で、見込みの払戻倍率が一定以上下がらない金額）を見積もる。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

#: 複勝の控除率（JRA）。
PLACE_TAKEOUT = 0.20
#: 複勝の的中馬の数（7頭以下は2頭だが、近似として3頭で数える）。
PLACE_WINNERS = 3
#: 許す払戻倍率の下がり幅。
ALLOWED_DROP = 0.05
#: 売上の票数1票の金額（円）。
YEN_PER_VOTE = 100


@dataclass(frozen=True)
class StakeCeilingSummary:
    """1点あたりの上限の金額（円）の分かれ方。"""

    bets: int
    lower_tenth: float
    median: float


class StakeCeiling:
    """1点に賭ける金額の上限の見積もり。

    複勝の払戻倍率は、おおよそ「複勝の売上 × (1 − 控除率) ÷ 的中馬の数 ÷ その馬に入った金額」なので、
    その馬に入った金額 V を、見込みの払戻倍率から逆に見積もる。自分が S 円を足すと倍率はおよそ V ÷ (V + S) 倍になる。
    倍率の下がりを ``ALLOWED_DROP`` までに抑える S を上限とする。近似なので、目安として使う。

    入力の列: 複勝プールの大きさ（票数）・想定払戻倍率（1頭ごとの見込みの倍率。100円あたりではなく倍）。
    """

    def per_bet(self, bought: pd.DataFrame) -> pd.Series:
        pool_yen = bought["複勝プールの大きさ"] * YEN_PER_VOTE
        horse_yen = pool_yen * (1 - PLACE_TAKEOUT) / PLACE_WINNERS / bought["想定払戻倍率"]
        return horse_yen * ALLOWED_DROP / (1 - ALLOWED_DROP)

    def summary(self, bought: pd.DataFrame) -> StakeCeilingSummary:
        ceiling = self.per_bet(bought).dropna()
        if ceiling.empty:
            return StakeCeilingSummary(bets=0, lower_tenth=0.0, median=0.0)
        return StakeCeilingSummary(bets=len(ceiling), lower_tenth=float(ceiling.quantile(0.1)),
                                   median=float(ceiling.median()))
