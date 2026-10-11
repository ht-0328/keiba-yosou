"""過去のレースに、年ごとの確かめの予測から展開スコアを付ける。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from yosou.race_development.workflow import PaceForecastHistory
from yosou.shared.feature import PredictionTiming

from .yearly_scorer import YearlyScorer


class ScoreHistory:
    """予想「展開から着順を予想」の年ごとの確かめの予測（``<development_root>/out_of_sample/``。その年より前だけで学習した
    展開のモデルの予測）を読み、``YearlyScorer`` で過去の出走ごとに展開スコアを付ける（線の確かめと研究用）。

    予測はあるが材料（``prepared``。``AdvantageRuns`` の表）に無いレース（障害など）の行は落とす。
    """

    def __init__(self, development_root: Path) -> None:
        self._history = PaceForecastHistory(Path(development_root))
        self._scorer = YearlyScorer()

    def of(self, timing: PredictionTiming, prepared: pd.DataFrame) -> pd.DataFrame:
        """1行 = 1頭（``DevelopmentScore.COLUMNS`` と ``race_date``）。予測が無ければ ``FileNotFoundError``。"""
        scored = self._scorer.of(self._history.read(timing), prepared)
        return scored[scored["race_date"].notna()].reset_index(drop=True)
