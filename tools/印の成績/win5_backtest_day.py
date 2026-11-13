"""過去の WIN5 の1日を、確かめに使う形で表す値。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Win5BacktestDay:
    """``legs`` は発売の順の5レースの確率の表（``RaceWinShare`` の結果。そろえた1着の確率・オッズから見た勝率・上乗せの列つき）、
    ``sources`` はレースごとに使った確率（当日・前日・オッズだけ）、``fold`` はその日を含む区切り、``carry`` はキャリーオーバー金額初期（円）。"""

    race_date: str
    fold: str
    saturday: bool
    carry: int
    legs: tuple[pd.DataFrame, ...]
    sources: tuple[str, ...]
