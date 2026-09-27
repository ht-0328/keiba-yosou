"""レースのペースを、ハイ・ミドル・スローに分ける（手順1で使った、今の測り方）。"""

from __future__ import annotations

import pandas as pd

from yosou.race_development.feature.history import RaceBaselineLookup
from yosou.race_development.feature.history.pace_baseline import FIRST_HALF_BASELINE, STD

from .pace_bands import PaceBands

#: 出力の列の名前。
PACE, PACE_Z, PACE_GAP = "ペース", "前半の速さ（z）", "前半タイムの基準との差（秒）"


class RacePaceClassifier:
    """1行 = 1レースの表に、前半タイムの基準と、ペースの区分を足す。

    前半タイムは JV-Data の前3ハロン（``first3f``）。基準は、展開予想（``src/yosou/race_development``）と同じ
    ``RaceBaselineLookup`` で作る（開催日の前日までの3年の、同じ競馬場・コース・距離・クラスの平均と標準偏差）。
    z =（基準 − 前半タイム）÷ 基準の標準偏差。速いほどプラスで、0.5 より大きければハイ、−0.5 より小さければスロー。
    例: 基準 35.1秒・標準偏差 0.6秒で、前半 34.6秒なら z = 0.83 でハイ。
    """

    def __init__(self) -> None:
        self._baselines = RaceBaselineLookup()
        self._bands = PaceBands()

    def classify(self, races: pd.DataFrame) -> pd.DataFrame:
        attached = self._baselines.attach(races)
        mean = pd.to_numeric(attached[FIRST_HALF_BASELINE], errors="coerce")
        std = pd.to_numeric(attached[FIRST_HALF_BASELINE + STD], errors="coerce")
        first3f = pd.to_numeric(attached["first3f"], errors="coerce")
        z = (mean - first3f) / std
        return attached.assign(**{PACE_Z: z, PACE_GAP: first3f - mean, PACE: self._bands.label(z)})
