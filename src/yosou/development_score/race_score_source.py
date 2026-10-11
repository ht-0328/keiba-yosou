"""これから走る1レースの展開スコアの表（予測用データに足す元）を作る。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from yosou.race_development.workflow import DevelopmentPaceWorkflow
from yosou.shared.dataset import OddsInput
from yosou.shared.feature import PredictionTiming

from .advantage_table import AdvantageTable
from .development_score import DevelopmentScore
from .race_course_repository import RaceCourseRepository


class RaceScoreSource:
    """1レースを、その時点の保存した展開のモデルで予測し（``DevelopmentPaceWorkflow``。①②③ の予測を使う）、表 G と掛け合わせて
    展開スコアの表（1行 = 1頭。``DevelopmentScore.COLUMNS``）にする。

    ``RaceScoreWorkflow``（道具）と、全頭の予想の予測の流れ（S を足して学んだ時点。``ScoreAttachment``）の両方が使う。
    ``models_root`` は予想「展開から着順を予想」の ``models/``。モデルが無ければ ``FileNotFoundError``。
    """

    def __init__(self, models_root: Path, table: AdvantageTable) -> None:
        self._development = DevelopmentPaceWorkflow(Path(models_root))
        self._table = table
        self._score = DevelopmentScore()

    def of(self, con: duckdb.DuckDBPyConnection, race_id: str, timing: PredictionTiming,
           given_odds: OddsInput | None = None) -> pd.DataFrame:
        course = RaceCourseRepository(con).read(race_id)
        forecasts = self._development.run(con, race_id, timing, given_odds)
        return self._score.of(forecasts, course, self._table)
