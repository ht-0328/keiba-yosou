"""過去のレースに、年ごとの確かめの展開の予測からバイアスの補正を付ける。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from yosou.race_development.workflow import PaceForecastHistory
from yosou.shared.feature import PredictionTiming

from .race_slopes import RaceSlopes
from .yearly_bias import YearlyBias


class BiasHistory:
    """予想「展開から着順を予想」の年ごとの確かめの予測（``<development_root>/out_of_sample/``。その年より前だけで学習した
    展開のモデルの予測の④ 4コーナーの位置）を読み、``YearlyBias`` で過去の出走ごとにバイアスの補正を付ける（研究と学習用）。

    ``runs`` は ``BiasRunRepository`` の表。レースごとの傾きはここで ``RaceSlopes`` で出す。
    予測はあるが材料に無いレース（障害など）の行は落とす。
    """

    def __init__(self, development_root: Path) -> None:
        self._history = PaceForecastHistory(Path(development_root))
        self._slopes = RaceSlopes()
        self._yearly = YearlyBias()

    def of(self, timing: PredictionTiming, runs: pd.DataFrame, slopes: pd.DataFrame | None = None) -> pd.DataFrame:
        """1行 = 1頭（``BiasCorrection.COLUMNS`` と ``race_date``）。予測が無ければ ``FileNotFoundError``。
        ``slopes`` を渡せば（``RaceSlopes.of(runs)`` を先に出してあれば）それを使う。"""
        if slopes is None:
            slopes = self._slopes.of(runs)
        corrected = self._yearly.of(self._history.read(timing), runs, slopes, timing)
        return corrected[corrected["race_date"].notna()].reset_index(drop=True)
