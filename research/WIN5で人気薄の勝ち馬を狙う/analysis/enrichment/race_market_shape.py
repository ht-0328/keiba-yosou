"""単勝オッズから、馬ごとの「オッズから見た勝率」と、レースごとの人気の割れ方の列を足す。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

#: 人気薄（この研究の対象）の人気の始まり。
LONGSHOT_POPULARITY = 10
#: 「人気になっている馬」とみなす単勝オッズ（この倍率未満の頭数を数える）。
CONTENDER_ODDS = 10.0


@dataclass(frozen=True)
class RaceMarketShape:
    """出走の表に次の列を足す。どれも単勝オッズ（確定）から作る。確定オッズは締め切り前のオッズとほぼ同じとみなす。

    - ``market``: オッズから見た勝率（単勝オッズの逆数を、レースの中で合計 1 にそろえたもの）
    - ``favorite_odds``: 1番人気の単勝オッズ
    - ``contenders``: 単勝 10倍未満の頭数
    - ``top3_market``: オッズから見た勝率の上位3頭の合計（人気が上位に固まっているほど大きい）
    - ``longshot_market``: 10番人気以下の馬のオッズから見た勝率の合計（市場が「人気薄が勝つ」と見た確率）
    - ``carried_gap``: 斤量 − レースの斤量の平均（kg）
    """

    def add(self, runners: pd.DataFrame) -> pd.DataFrame:
        frame = runners.copy()
        race = frame["race_id"]
        inverse = 1.0 / frame["win_odds"].where(frame["win_odds"] > 0)
        frame["market"] = inverse / inverse.groupby(race).transform("sum")
        frame["favorite_odds"] = frame["win_odds"].groupby(race).transform("min")
        frame["contenders"] = (frame["win_odds"] < CONTENDER_ODDS).astype(float).groupby(race).transform("sum")
        ranked = frame["market"].groupby(race).rank(ascending=False, method="first")
        frame["top3_market"] = frame["market"].where(ranked <= 3).groupby(race).transform("sum")
        longshot = frame["market"].where(frame["popularity"] >= LONGSHOT_POPULARITY, 0.0)
        frame["longshot_market"] = longshot.groupby(race).transform("sum")
        frame["carried_gap"] = frame["carried"] - frame["carried"].groupby(race).transform("mean")
        return frame
