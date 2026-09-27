"""切り口ごとの成績を数える。"""

from __future__ import annotations

import pandas as pd

from .market_win_probability import MARKET_WIN

#: 出力の列（% の値）。
COLUMNS: tuple[str, ...] = ("頭数", "勝率", "複勝率", "単勝回収率", "複勝回収率", "オッズから見た勝率", "勝率とオッズの差")


class PerformanceTally:
    """出走の表を ``keys`` で分けて、``COLUMNS`` を出す（割合と回収率は %）。

    - 複勝率は3着以内の割合（7頭以下のレースも3着以内で数える）。回収率は 100円ずつ買ったときの払戻の割合。
    - 勝率とオッズの差 = 勝率 − オッズから見た勝率。プラスなら、市場が見ていたより勝った（馬の力では説明できない分）。
    """

    def tally(self, runners: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
        frame = runners.assign(_win=(runners["finish"] == 1).astype(float),
                               _top3=(runners["finish"] <= 3).fillna(False).astype(float))
        grouped = frame.groupby(keys, observed=True)
        table = pd.DataFrame({
            "頭数": grouped.size(),
            "勝率": grouped["_win"].mean() * 100,
            "複勝率": grouped["_top3"].mean() * 100,
            "単勝回収率": grouped["win_payout"].mean(),
            "複勝回収率": grouped["place_payout"].mean(),
            "オッズから見た勝率": grouped[MARKET_WIN].mean() * 100,
        })
        return table.assign(勝率とオッズの差=table["勝率"] - table["オッズから見た勝率"])
