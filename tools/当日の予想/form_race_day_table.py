"""一般の予想「近走と適性から3着以内を予想」の当日の予測を、1レースの表にする。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from 共通.render import Table

from yosou.ability_score import RaceAbilityScoreAttacher
from yosou.form_aptitude_top3.command.development_root_argument import DEFAULT_DEVELOPMENT_ROOT
from yosou.form_aptitude_top3.dataset import OddsResolver, race_day_dataset_builder
from yosou.form_aptitude_top3.feature import WIN_ODDS
from yosou.form_aptitude_top3.workflow import (
    ABILITY_SCORE_TOP3_TIMINGS,
    POOL_FREE_FOLDER,
    PROBABILITY,
    TRACK_BIAS_TOP3_TIMINGS,
    WEIGHT_DISCOUNT_TOP3_TIMINGS,
    DataAttachment,
    PredictionWorkflow,
)
from yosou.track_bias import MemoizedPaceForecast, PriorSlopeTableStore, RaceBiasAttacher, bias_cache_folder_beside
from yosou.weight_table import RaceWeightDiscountAttacher, WeightTableStore, weight_cache_folder_beside
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
    券種オッズなしのモデル。複勝の見込みの倍率があれば期待値も。能力スコア（T）・トラックバイアスの補正（U）を当日の3着以内のモデルに
    採用していれば、それも足す）。``models`` は学習済みのモデルの置き場所、``figure_cache`` はスピード指数をとっておく場所、
    ``development_root`` は予想「展開から着順を予想」の置き場所（U に要る）。モデルが無ければ ``FileNotFoundError``。
    """

    def __init__(self, models: Path, figure_cache: Path = DEFAULT_FOLDER, development_root: Path = DEFAULT_DEVELOPMENT_ROOT) -> None:
        self._models = Path(models)
        self._figure_cache = Path(figure_cache)
        self._development_root = Path(development_root)

    def table(self, con: duckdb.DuckDBPyConnection, race_id: str) -> Table:
        workflow = PredictionWorkflow(
            race_day_dataset_builder(con, self._figure_cache), SegmentedPrediction(ModelSegments(), self._models),
            OddsResolver(AnnouncedOddsRepository(con)), PlaceValueColumns(self._place_price()),
            pool_free=SegmentedPrediction(ModelSegments(), self._models / POOL_FREE_FOLDER),
            extras=self._extras(con),
        )
        prediction = workflow.run(race_id, TIMING)
        return PredictionTable(prediction, TIMING, PROBABILITY, self._extra_columns(prediction)).table()

    def _extras(self, con: duckdb.DuckDBPyConnection) -> list[DataAttachment]:
        """当日の3着以内のモデルに採用した材料（T・U・V）を予測用データに足す関数。"""
        extras: list[DataAttachment] = []
        if TIMING in ABILITY_SCORE_TOP3_TIMINGS:
            extras.append(RaceAbilityScoreAttacher().attach)
        if TIMING in TRACK_BIAS_TOP3_TIMINGS:
            slopes, table = PriorSlopeTableStore(bias_cache_folder_beside(self._development_root)).load(con)
            extras.append(RaceBiasAttacher(con, MemoizedPaceForecast(self._development_root / "models").run, slopes, table).attach)
        if TIMING in WEIGHT_DISCOUNT_TOP3_TIMINGS:
            extras.append(RaceWeightDiscountAttacher(WeightTableStore(weight_cache_folder_beside(self._development_root)).load(con)).attach)
        return extras

    def has_models(self) -> bool:
        """当日のモデルが置いてあるか。"""
        return (self._models / TIMING.value).is_dir()

    def _extra_columns(self, prediction: pd.DataFrame) -> list[str]:
        return [column for column in (WIN_ODDS, TOP3_RATE, PLACE_PROBABILITY, PLACE_VALUE) if column in prediction.columns]

    def _place_price(self) -> PlacePriceEstimator | None:
        state = PlacePriceRepository(self._models).load()
        return PlacePriceEstimator.from_state(state) if state is not None else None
