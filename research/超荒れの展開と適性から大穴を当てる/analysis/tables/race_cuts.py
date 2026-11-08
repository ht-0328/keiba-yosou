"""1行 = 1レースの表を分ける切り口（表の見出し → 値を作る関数）。"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd


def distance_band(distance: pd.Series) -> pd.Series:
    return pd.cut(distance, [0, 1400, 1800, 2200, 4000], labels=["〜1400m", "1401〜1800m", "1801〜2200m", "2201m〜"])


def _field_band(races: pd.DataFrame) -> pd.Series:
    return pd.cut(races["field_size"], [0, 10, 12, 14, 16, 18],
                  labels=["〜10頭", "11〜12頭", "13〜14頭", "15〜16頭", "17〜18頭"])


def _spread_band(races: pd.DataFrame) -> pd.Series:
    return pd.cut(races["carried_spread"], [-1, 2.5, 4.5, 6.5, 30], labels=["〜2kg", "3〜4kg", "5〜6kg", "7kg〜"])


def _market_band(races: pd.DataFrame) -> pd.Series:
    return pd.cut(races["longshot_market"], [-0.01, 0.03, 0.06, 0.09, 0.12, 1.0],
                  labels=["〜0.03", "0.03〜0.06", "0.06〜0.09", "0.09〜0.12", "0.12〜"])


CUTS: dict[str, Callable[[pd.DataFrame], pd.Series]] = {
    "年": lambda r: r["year"].astype(int).astype(str),
    "競馬場": lambda r: r["venue"],
    "芝ダ": lambda r: r["surface"],
    "距離": lambda r: distance_band(r["distance_m"]),
    "頭数": _field_band,
    "クラス": lambda r: r["class_name"],
    "馬場状態": lambda r: r["condition"],
    "重量種別": lambda r: r["weight_type"],
    "ハンデ戦か": lambda r: r["handicap"],
    "斤量の幅（いちばん重い − いちばん軽い）": _spread_band,
    "大穴のオッズから見た勝率の合計": _market_band,
    "結果のペース": lambda r: r["pace"].fillna("（不明）"),
    "予想のペース": lambda r: r["forecast_band"],
    "コースの単位（競馬場・コース・距離・馬場状態）": lambda r: (r["venue"] + r["course"] + r["distance_m"].astype(int).astype(str)
                                                  + "m・" + r["condition"]),
}
