"""◎と1番人気の3着以内率をまとめる。"""

from __future__ import annotations

import pandas as pd

from .top_pick_table import FAVORITE_SUFFIX

_FAVORITE_HIT = f"3着以内{FAVORITE_SUFFIX}"


class TopPickSummary:
    """``TopPickTable`` の表から、1行のまとめを作る。

    - ◎の3着以内率・1番人気の3着以内率・差（◎ − 1番人気）
    - 上回った区切り: 7つの区切りのうち、◎の3着以内率が1番人気より高かった数
    - 疑った割合: ◎が1番人気でないレースの割合。疑ったレースだけの◎と1番人気の3着以内率
    """

    def row(self, races: pd.DataFrame, label: str) -> dict[str, object]:
        doubted = races[races["疑った"]]
        by_window = races.groupby("区切り")[["3着以内", _FAVORITE_HIT]].mean()
        return {
            "作り方": label, "レース": len(races),
            "◎の3着以内率": round(races["3着以内"].mean(), 4), "1番人気の3着以内率": round(races[_FAVORITE_HIT].mean(), 4),
            "差": round(races["3着以内"].mean() - races[_FAVORITE_HIT].mean(), 4),
            "上回った区切り": f"{int((by_window['3着以内'] > by_window[_FAVORITE_HIT]).sum())} / {len(by_window)}",
            "疑った割合": round(len(doubted) / len(races), 3),
            "疑ったレースの◎": round(doubted["3着以内"].mean(), 4),
            "疑ったレースの1番人気": round(doubted[_FAVORITE_HIT].mean(), 4),
        }
