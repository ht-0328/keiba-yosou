"""◎の確率の高さごとに、◎と同じレースの1番人気の3着以内率を出す。"""

from __future__ import annotations

import pandas as pd

from .top_pick_table import FAVORITE_SUFFIX

#: ◎の確率の帯の区切り。
EDGES: tuple[float, ...] = (0.0, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0)


class ConfidenceBands:
    """``TopPickTable`` の表を、◎の確率（``score``）の帯で分ける。

    オッズを見ずに「◎が堅いレース」を見分けられるかを確かめる。帯の◎の3着以内率が、帯の確率に近く、
    確率が高い帯ほど高ければ、見分けられている。
    """

    def table(self, races: pd.DataFrame) -> pd.DataFrame:
        band = pd.cut(races["score"], list(EDGES))
        groups = races.groupby(band, observed=True)
        table = pd.DataFrame({
            "レース": groups.size(), "レースの割合": groups.size() / len(races),
            "◎の3着以内率": groups["3着以内"].mean(), "同じレースの1番人気": groups[f"3着以内{FAVORITE_SUFFIX}"].mean(),
            "◎が1番人気の割合": groups["疑った"].apply(lambda doubted: 1 - doubted.mean()),
        })
        table.index = [f"{interval.left:.1f}〜{interval.right:.1f}" for interval in table.index]
        return table.round(3)
