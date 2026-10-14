"""これから走る1レースの展開スコアの結果（人が見る形）の入れ物。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from yosou.shared.feature import PredictionTiming

from . import names
from .repository import HORSE_NAME, HORSE_NO

#: 1頭ごとの表の列の並び。
HORSE_COLUMNS: tuple[str, ...] = (HORSE_NO, HORSE_NAME, "horse_id", *names.STYLES, *names.CONTRIBUTIONS, names.SCORE, names.VERDICT)


@dataclass(frozen=True)
class RaceScore:
    """1レースの結果。``paces`` はレースのペースの確率（スロー・平均・ハイ）、``horses`` は 1行 = 1頭（``HORSE_COLUMNS``。
    展開スコアの高い順）、``venue_code``・``surface`` は表 G を引いた競馬場と芝ダ。"""

    race_id: str
    timing: PredictionTiming
    venue_code: str
    surface: str
    paces: pd.Series
    horses: pd.DataFrame
