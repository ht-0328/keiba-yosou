"""これから走る1レースの展開スコアと判定を出す。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from yosou.shared.dataset import OddsInput
from yosou.shared.feature import PredictionTiming

from . import names
from .advantage_judge import AdvantageJudge
from .advantage_table import AdvantageTable
from .race_score import HORSE_COLUMNS, RaceScore
from .race_score_source import RaceScoreSource
from .repository import EntryNameRepository, RaceCourseRepository


class RaceScoreWorkflow:
    """1レースの展開スコアの表（``RaceScoreSource``）に判定と馬番・馬名を付け、人が見る形（``RaceScore``）にする。
    ほかのクラスを順に呼ぶだけで、自分では計算しない。

    ``models_root`` は予想「展開から着順を予想」の ``models/``。モデルが無ければ ``FileNotFoundError``。
    呼ぶ側が開いている元DB の接続を受け取る。
    """

    def __init__(self, models_root: Path, table: AdvantageTable, judge: AdvantageJudge) -> None:
        self._source = RaceScoreSource(models_root, table)
        self._judge = judge

    def run(self, con: duckdb.DuckDBPyConnection, race_id: str, timing: PredictionTiming,
            given_odds: OddsInput | None = None) -> RaceScore:
        course = RaceCourseRepository(con).read(race_id)
        scored = self._source.of(con, race_id, timing, given_odds)
        scored[names.VERDICT] = self._judge.of(scored[names.SCORE])
        entries = EntryNameRepository(con).read(race_id)
        horses = scored.assign(horse_id=scored["horse_id"].astype(str)).merge(entries, on="horse_id", how="left")
        horses = horses.sort_values(names.SCORE, ascending=False, kind="stable").reset_index(drop=True)
        paces = scored[list(names.PACES)].iloc[0] if len(scored) else pd.Series(dtype="float64", index=list(names.PACES))
        return RaceScore(race_id, timing, str(course[names.VENUE_CODE].iloc[0]), str(course[names.SURFACE].iloc[0]),
                         paces, horses[list(HORSE_COLUMNS)])
