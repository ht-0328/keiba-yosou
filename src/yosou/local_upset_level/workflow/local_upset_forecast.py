"""これから走る（か終わった）1レースの、券種ごとの荒れ具合の確率を出す入口。"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import duckdb
import pandas as pd

from yosou.shared.dataset import OddsInput, OddsResolver
from yosou.shared.feature import PredictionTiming
from yosou.shared.repository import AnnouncedOddsRepository
from yosou.upset_level.dataset import BetType
from yosou.upset_level.workflow import BET, UPSET_OR_MORE, PredictionWorkflow, model_repositories

from ..dataset import local_race_dataset_builder
from ..feature import RaceUsedSlopes
from ..repository import PriorSlopeYearStore
from .prediction_timings import DEFAULT_CACHE_DIR, DEFAULT_MODELS_DIR


class LocalUpsetForecast:
    """1レースの U（当日の使う内の傾き・使う前の傾き。``RaceUsedSlopes``）を先に出し、それを渡した ``RaceDatasetBuilder``
    （``local_race_dataset_builder``）と、中央の荒れ具合と同じ ``PredictionWorkflow`` で、券種ごとの4つの確率を出す（設計書 05 の図2）。

    ``predict`` コマンドと、道具「地方の推奨買目」（3連複の「中荒れ以上の確率」の条件）が使う。呼ぶ側が開いている元DB の接続を受け取る。
    ``models`` は学習したモデルの置き場所（``<券種>/<時点>/``）、``cache`` は過去の傾きの表のとっておき（無ければ元DB から作る。1分ほど）。
    """

    def __init__(self, models: Path = DEFAULT_MODELS_DIR, cache: Path = DEFAULT_CACHE_DIR) -> None:
        self._models = Path(models)
        self._cache = Path(cache)

    def run(self, con: duckdb.DuckDBPyConnection, race_id: str, timing: PredictionTiming, given: OddsInput | None = None,
            bets: Sequence[BetType] | None = None) -> pd.DataFrame:
        """1レースの、券種ごとの荒れ具合の確率（1行 = 1券種。列は ID 列と ``PREDICTION_COLUMNS``）。
        モデルが無ければ ``FileNotFoundError``、要る情報（馬場状態・全頭のオッズ・1番人気の馬体重）が無ければ ``ValueError``。"""
        slopes = RaceUsedSlopes(con, PriorSlopeYearStore(self._cache)).of(race_id, timing)
        workflow = PredictionWorkflow(
            local_race_dataset_builder(con, slopes), model_repositories(self._models), OddsResolver(AnnouncedOddsRepository(con)),
        )
        return workflow.run(race_id, timing, given, bets)

    def upset_or_more(self, con: duckdb.DuckDBPyConnection, race_id: str, timing: PredictionTiming = PredictionTiming.RACE_DAY,
                      bets: Sequence[BetType] | None = None) -> dict[BetType, float]:
        """券種 → 中荒れ以上の確率（固い以外の3つの合計）。推奨買目が使う形。"""
        table = self.run(con, race_id, timing, bets=bets)
        return {BetType.parse(str(row[BET])): float(row[UPSET_OR_MORE]) for _, row in table.iterrows()}
