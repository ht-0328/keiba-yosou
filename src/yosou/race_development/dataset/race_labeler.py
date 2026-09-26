"""③ 前半のペースと ⑥ 後半のペースの目的変数を付ける。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.feature import as_numbers

from ..feature.history import FIRST_HALF_BASELINE, MEAN, SECOND_HALF_BASELINE, STD
from . import label_names as names

#: ペースの区分の線（基準の標準偏差の何倍か。設計書 10 の 4）。
PACE_Z_LIMIT = 0.5


class RaceLabeler:
    """1レースごとの学習データ（③⑥）の目的変数を付ける（設計書 06 の図2b・10 の 4.・9.）。``RaceTargetLabeler`` を守る。

    - ペースの区分: ``z = (基準 − 前半タイム) ÷ 標準偏差`` が 0.5 より大きければハイ（2）、−0.5 より小さければスロー（0）、
      ほかは平均（1）。
    - 前半タイムの基準との差: 前半タイム − 基準（秒）。
    - 後半タイムの基準との差: 後半タイム − 後半タイムの基準（秒）。区分は作らない。
    タイムか基準が無いレースは欠損値。
    """

    @property
    def label_names(self) -> tuple[str, ...]:
        return names.PACE_CLASS, names.FIRST_HALF_DIFF, names.SECOND_HALF_DIFF

    def build(self, races: pd.DataFrame) -> pd.DataFrame:
        """``races`` は ``PaceRecordSource`` の表（index はレースID）。行の並びと index は ``races`` と同じ。"""
        first_half = as_numbers(races["first3f"])
        baseline = as_numbers(races[FIRST_HALF_BASELINE + MEAN])
        z = (baseline - first_half) / as_numbers(races[FIRST_HALF_BASELINE + STD])
        pace = np.select([z > PACE_Z_LIMIT, z < -PACE_Z_LIMIT], [2.0, 0.0], default=1.0)
        second_half_diff = as_numbers(races["last3f_race"]) - as_numbers(races[SECOND_HALF_BASELINE + MEAN])
        return pd.DataFrame({
            names.PACE_CLASS: pd.Series(pace, index=races.index).where(z.notna()),
            names.FIRST_HALF_DIFF: first_half - baseline,
            names.SECOND_HALF_DIFF: second_half_diff,
        }, index=races.index)
