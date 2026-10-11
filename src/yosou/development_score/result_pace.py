"""レースごとに、結果のペース（スロー・平均・ハイ）を付ける。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.race_development.dataset.race_labeler import PACE_Z_LIMIT
from yosou.race_development.feature.history import FIRST_HALF_BASELINE, MEAN, STD, RaceBaselineLookup
from yosou.shared.feature import as_numbers

from . import names

#: 1レースに1つの値の列（基準を付けるのに要るもの）。
_RACE_COLUMNS: tuple[str, ...] = (
    "race_id", "race_date", "venue_code", "track_code", "distance_m", "class_order", "first3f", "last3f_race",
)


class ResultPace:
    """出走の表から、レースごとの結果のペースを出す。

    前3ハロンを、展開の予想と同じ基準（開催日の前日までの3年の、同じ競馬場・コース・距離・クラスのレースの平均と標準偏差。
    ``RaceBaselineLookup``）と比べた ``z = (基準 − 前半タイム) ÷ 標準偏差`` を、展開の予想③の目的変数と同じ線（0.5）で
    ハイ・平均・スローに分ける（展開の予想の設計書 10 の 4）。③ の確率と掛け合わせるので、区分の決め方を ③ とそろえる。
    基準が作れないレース（件数が足りない）や前半タイムの無いレースは欠損値。
    """

    def __init__(self) -> None:
        self._baselines = RaceBaselineLookup()

    def of(self, runs: pd.DataFrame) -> pd.Series:
        """レースID → ペース（``names.PACES`` のどれか、または欠損値）。"""
        races = runs.drop_duplicates("race_id")[list(_RACE_COLUMNS)].reset_index(drop=True)
        attached = self._baselines.attach(races)
        mean, std = as_numbers(attached[FIRST_HALF_BASELINE + MEAN]), as_numbers(attached[FIRST_HALF_BASELINE + STD])
        z = (mean - as_numbers(attached["first3f"])) / std
        pace = np.select([z > PACE_Z_LIMIT, z < -PACE_Z_LIMIT, z.notna()], [names.HIGH, names.SLOW, names.EVEN], default=None)
        return pd.Series(pace, index=attached["race_id"].to_numpy(), dtype="object")
