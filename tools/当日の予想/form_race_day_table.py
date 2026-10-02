"""一般の予想「近走と適性から3着以内を予想」の当日の予測を、1レースの表にする。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from 共通.render import Table

from yosou.form_aptitude_top3.dataset import OddsResolver, race_day_dataset_builder
from yosou.form_aptitude_top3.feature import WIN_ODDS
from yosou.form_aptitude_top3.workflow import POOL_FREE_FOLDER, PROBABILITY, PredictionWorkflow
from yosou.shared.command import PredictionTable
from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.odds import TOP3_RATE
from yosou.shared.place_value import PLACE_PROBABILITY, PLACE_VALUE, PlacePriceEstimator, PlaceValueColumns
from yosou.shared.repository import AnnouncedOddsRepository, PlacePriceRepository
from yosou.shared.repository.speed_figure_repository import DEFAULT_FOLDER
from yosou.shared.workflow import ModelSegments, SegmentedPrediction

#: 当日の予想は発走の前に出すので、「当日」の時点のモデルを使う。
TIMING = PredictionTiming.RACE_DAY


class FormRaceDayTable:
    """一般の予想（近走と適性）の当日のモデルで1レースを予測し、確率の高い順の表にする。

    ``python -m yosou.form_aptitude_top3 predict --timing 当日`` と同じ組み立て（当日の材料。券種のオッズが無ければ
    券種オッズなしのモデル。複勝の見込みの倍率があれば期待値も）。``models`` は学習済みのモデルの置き場所、
    ``figure_cache`` はスピード指数をとっておく場所。モデルが無ければ ``FileNotFoundError``。
    """

    def __init__(self, models: Path, figure_cache: Path = DEFAULT_FOLDER) -> None:
        self._models = Path(models)
        self._figure_cache = Path(figure_cache)

    def table(self, con: duckdb.DuckDBPyConnection, race_id: str) -> Table:
        workflow = PredictionWorkflow(
            race_day_dataset_builder(con, self._figure_cache), SegmentedPrediction(ModelSegments(), self._models),
            OddsResolver(AnnouncedOddsRepository(con)), PlaceValueColumns(self._place_price()),
            pool_free=SegmentedPrediction(ModelSegments(), self._models / POOL_FREE_FOLDER),
        )
        prediction = workflow.run(race_id, TIMING)
        return PredictionTable(prediction, TIMING, PROBABILITY, self._extra_columns(prediction)).table()

    def has_models(self) -> bool:
        """当日のモデルが置いてあるか。"""
        return (self._models / TIMING.value).is_dir()

    def _extra_columns(self, prediction: pd.DataFrame) -> list[str]:
        return [column for column in (WIN_ODDS, TOP3_RATE, PLACE_PROBABILITY, PLACE_VALUE) if column in prediction.columns]

    def _place_price(self) -> PlacePriceEstimator | None:
        state = PlacePriceRepository(self._models).load()
        return PlacePriceEstimator.from_state(state) if state is not None else None
