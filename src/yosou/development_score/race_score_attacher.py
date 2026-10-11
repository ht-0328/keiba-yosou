"""これから走る1レースの予測用データに、展開スコアを足す（予測の流れに渡す関数の形）。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from yosou.shared.dataset import OddsInput, PredictionData
from yosou.shared.feature import PredictionTiming

from .advantage_table import AdvantageTable
from .race_score_source import RaceScoreSource
from .score_attachment import ScoreAttachment


class RaceScoreAttacher:
    """``RaceScoreSource`` で作った展開スコアの表を、予測用データに ``ScoreAttachment`` で足す。

    全頭の予想の予測の流れ（``PredictionWorkflow``）の ``extras``・``win_extras`` に渡す関数の形（``attach``）。
    同じレース・同じ時点で続けて呼ばれたら（3着以内のモデルと1着のモデルの両方に足すとき）、展開のモデルを2回動かさずに
    前の表を使い回す。呼ぶ側が開いている元DB の接続を受け取る。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, models_root: Path, table: AdvantageTable) -> None:
        self._con = con
        self._source = RaceScoreSource(models_root, table)
        self._attachment = ScoreAttachment()
        self._last: tuple[tuple[str, PredictionTiming], pd.DataFrame] | None = None

    def attach(self, data: PredictionData, race_id: str, timing: PredictionTiming, given: OddsInput | None) -> PredictionData:
        key = (race_id, timing)
        if self._last is None or self._last[0] != key:
            self._last = (key, self._source.of(self._con, race_id, timing, given))
        return self._attachment.apply(data, self._last[1])
