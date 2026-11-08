"""人気薄が勝ったレースの分布の表（年・競馬場・芝ダ・距離・頭数・クラス・重量種別・馬場状態・人気の割れ方）。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from .cells import percent, ratio


def _distance_band(races: pd.DataFrame) -> pd.Series:
    return pd.cut(races["distance_m"], [0, 1400, 1800, 2200, 4000], labels=["〜1400m", "1401〜1800m", "1801〜2200m", "2201m〜"])


def _field_band(races: pd.DataFrame) -> pd.Series:
    return pd.cut(races["field_size"], [0, 10, 12, 14, 16, 18], labels=["〜10頭", "11〜12頭", "13〜14頭", "15〜16頭", "17〜18頭"])


def _favorite_band(races: pd.DataFrame) -> pd.Series:
    return pd.cut(races["favorite_odds"], [0, 2, 3, 4, 5, 100], labels=["〜2.0倍", "2.1〜3.0倍", "3.1〜4.0倍", "4.1〜5.0倍", "5.1倍〜"])


def _longshot_band(races: pd.DataFrame) -> pd.Series:
    return pd.cut(races["longshot_market"], [-0.01, 0.03, 0.06, 0.09, 0.12, 1.0],
                  labels=["〜0.03", "0.03〜0.06", "0.06〜0.09", "0.09〜0.12", "0.12〜"])


#: 切り口（表の見出し → レースの表から値を作る関数）。
CUTS: dict[str, Callable[[pd.DataFrame], pd.Series]] = {
    "年": lambda r: r["year"].astype(int).astype(str),
    "競馬場": lambda r: r["venue"],
    "芝ダ": lambda r: r["surface"],
    "距離": _distance_band,
    "頭数": _field_band,
    "クラス": lambda r: r["class_name"],
    "重量種別": lambda r: r["weight_type"],
    "馬場状態": lambda r: r["condition"],
    "1番人気の単勝オッズ": _favorite_band,
    "10番人気以下のオッズから見た勝率の合計": _longshot_band,
    "コースの単位（競馬場・芝ダ・距離・馬場状態）": lambda r: (r["venue"] + r["surface"] + r["distance_m"].astype(int).astype(str)
                                                 + "m・" + r["condition"]),
}


@dataclass(frozen=True)
class LongshotDistributionTable:
    """切り口ごとに、レース数・人気薄が勝ったレース数・割合・市場が見た数・実際 ÷ 市場 を並べる。"""

    def build(self, races: pd.DataFrame, cut: str, title: str, by_count: bool = False) -> Table:
        """``by_count`` なら、人気薄が勝った数の多い順に並べる（値の種類が多い切り口のため）。"""
        values = CUTS[cut](races)
        grouped = races.assign(cut=values).groupby("cut", observed=True)
        summary = grouped.agg(races=("longshot_won", "size"), won=("longshot_won", "sum"), market=("longshot_market", "sum"))
        if by_count:
            summary = summary.sort_values(["won", "races"], ascending=False)
        rows = [
            [str(value), int(row.races), int(row.won), percent(row.won, row.races), f"{row.market:.1f}", ratio(row.won, row.market)]
            for value, row in summary.iterrows()
        ]
        return Table([cut, "レース数", "人気薄が勝った", "割合", "市場が見た数", "実際 ÷ 市場"], rows, title=title)
