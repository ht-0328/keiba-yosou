"""大穴が勝ったレースで、大穴の中を並べたとき、勝ち馬を上位何頭に置けたかの表（人気の順・前の見込みの順・でたらめ）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from .cells import percent

TOPS: tuple[int, ...] = (1, 2, 3, 5)


@dataclass(frozen=True)
class RankCaptureTable:
    """``longshots`` は大穴が勝ったレースの大穴の行。並べ方は 人気の順（単勝オッズの小さい順）と、前の見込みの順
    （展開の予想の、前3分の1を取る確率の大きい順）。どちらも展開の予想のあるレースだけで比べる。"""

    def build(self, longshots: pd.DataFrame, title: str) -> Table:
        known = longshots.loc[longshots.groupby("race_id")["p_front"].transform(lambda s: s.notna().all())]
        winners = known["won"] > 0
        orders = {
            "人気の順": known.groupby("race_id")["win_odds"].rank(method="first"),
            "前の見込みの順": known.groupby("race_id")["p_front"].rank(method="first", ascending=False),
        }
        races = int(winners.sum())
        rows = [[name, races, *[percent((rank[winners] <= top).sum(), races) for top in TOPS]] for name, rank in orders.items()]
        sizes = known.groupby("race_id").size()
        rows.append(["でたらめ（目安）", races, *[f"{(sizes.clip(upper=top) / sizes).mean() * 100:.1f}%" for top in TOPS]])
        return Table(["大穴の中の並べ方", "レース数", *[f"上位{top}頭" for top in TOPS]], rows, title=title,
                     note=f"1レースの大穴は平均 {sizes.mean():.1f}頭。")
