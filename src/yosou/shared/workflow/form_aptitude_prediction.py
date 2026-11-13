"""今のモデル（予想「近走と適性から3着以内を予想」）の予測の流れを、時点に合わせて組み立てて、1レースを予測する。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from ..dataset import DatasetBuilder, OddsInput, OddsResolver
from ..dataset.form_aptitude_assembly import ability_dataset_builder, race_day_dataset_builder
from ..feature import PredictionTiming
from ..place_value import PlacePriceEstimator, PlaceValueColumns
from ..repository import AnnouncedOddsRepository, PlacePriceRepository
from ..repository.speed_figure_repository import DEFAULT_FOLDER
from .explained_prediction import ExplainedPrediction
from .form_aptitude_materials import FormAptitudeMaterials, MaterialsFactory
from .form_aptitude_timings import (
    ABILITY_SCORE_TOP3_TIMINGS,
    ABILITY_SCORE_WIN_TIMINGS,
    ABILITY_TIMINGS,
    PACE_TIMINGS,
    POOL_FREE_FOLDER,
    SCORE_TOP3_TIMINGS,
    SCORE_WIN_TIMINGS,
    TRACK_BIAS_TOP3_TIMINGS,
    TRACK_BIAS_WIN_TIMINGS,
    WEIGHT_DISCOUNT_TOP3_TIMINGS,
    WEIGHT_DISCOUNT_WIN_TIMINGS,
    WIN_FOLDER,
)
from .model_segments import ModelSegments
from .prediction_workflow import DataAttachment, PredictionWorkflow
from .segmented_prediction import SegmentedPrediction


class FormAptitudePrediction:
    """今のモデルの学習済みモデルで、1レースの全頭の「3着以内に入る確率」と「1着になる確率」を出す。

    時点に合わせて、材料の組み立て（木曜・前日は馬の力の材料、当日は今の材料と券種の支持と馬の力の材料）・材料を足す関数
    （P・S・T・U・V。採用した時点だけ）・モデルの置き場所（3着以内・1着・券種オッズなし）を選んで ``PredictionWorkflow`` を作る
    （設計書「近走と適性から3着以内を予想」05 の図2）。当日に券種のオッズが無いレースは、``PredictionWorkflow`` が券種オッズなしの
    モデルに切り替える。今のモデルのコマンド（``predict``）・道具「今週の予想」・予想「近走と適性からWIN5の買い目を決める」が
    同じ組み立てで予測するので ``shared`` に置く（設計書「近走と適性からWIN5の買い目を決める」04 の 1）。

    ``models`` は今のモデルの学習済みモデルの置き場所（``reports/近走と適性から3着以内を予想/models``）。
    ``materials`` は、元DB への接続から材料を作る部品（``FormAptitudeMaterials``）を作る関数。予測のたびに1つ作り、
    その予測の3着以内と1着のモデルで使い回す。``figure_cache`` はスピード指数をとっておく場所。
    """

    def __init__(self, models: Path, materials: MaterialsFactory, figure_cache: Path = DEFAULT_FOLDER) -> None:
        self._models = Path(models)
        self._materials = materials
        self._figure_cache = Path(figure_cache)

    def run(self, con: duckdb.DuckDBPyConnection, race_id: str, timing: PredictionTiming,
            given: OddsInput | None = None) -> pd.DataFrame:
        """1レースの全頭の予測の表（``PredictionWorkflow.run`` と同じ列。``PROBABILITY``・``WIN_PROBABILITY``・単勝オッズ など）。
        ``given`` は利用者が渡したオッズ（省略すると、元DB から決める）。"""
        return self.workflow(con, timing).run(race_id, timing, given)

    def explain(self, con: duckdb.DuckDBPyConnection, race_id: str, timing: PredictionTiming,
                given: OddsInput | None = None) -> ExplainedPrediction:
        """``run`` と同じ予測に、特徴量の値と特徴量ごとの寄与を添える（``PredictionWorkflow.explain``）。"""
        return self.workflow(con, timing).explain(race_id, timing, given)

    def workflow(self, con: duckdb.DuckDBPyConnection, timing: PredictionTiming) -> PredictionWorkflow:
        """その時点の予測の流れ。材料を作る部品は、ここで1つ作る。"""
        materials = self._materials(con)
        return PredictionWorkflow(
            self._dataset_builder(con, timing), self._segmented(self._models),
            OddsResolver(AnnouncedOddsRepository(con)), PlaceValueColumns(self._place_price()),
            pool_free=self._segmented(self._models / POOL_FREE_FOLDER),
            pace=materials.pace() if timing in PACE_TIMINGS else None,
            win_predictor=self._segmented(self._models / WIN_FOLDER),
            win_pool_free=self._segmented(self._models / POOL_FREE_FOLDER / WIN_FOLDER),
            extras=self._extras(materials, timing, SCORE_TOP3_TIMINGS, ABILITY_SCORE_TOP3_TIMINGS, TRACK_BIAS_TOP3_TIMINGS,
                                WEIGHT_DISCOUNT_TOP3_TIMINGS),
            win_extras=self._extras(materials, timing, SCORE_WIN_TIMINGS, ABILITY_SCORE_WIN_TIMINGS, TRACK_BIAS_WIN_TIMINGS,
                                    WEIGHT_DISCOUNT_WIN_TIMINGS),
        )

    def _dataset_builder(self, con: duckdb.DuckDBPyConnection, timing: PredictionTiming) -> DatasetBuilder:
        """その時点のモデルの材料の組み立て。木曜・前日は馬の力の材料、当日は今の材料と券種の支持と馬の力の材料。"""
        if timing in ABILITY_TIMINGS:
            return ability_dataset_builder(con, self._figure_cache)
        return race_day_dataset_builder(con, self._figure_cache)

    def _segmented(self, root: Path) -> SegmentedPrediction:
        """``root`` に保存したモデルでの予測（今のモデルは区分に分けない）。"""
        return SegmentedPrediction(ModelSegments(), root)

    def _extras(self, materials: FormAptitudeMaterials, timing: PredictionTiming, score_timings: tuple[PredictionTiming, ...],
                ability_score_timings: tuple[PredictionTiming, ...], track_bias_timings: tuple[PredictionTiming, ...],
                weight_discount_timings: tuple[PredictionTiming, ...]) -> list[DataAttachment]:
        """そのモデルの予測用データに足す材料の関数。展開スコア（S）を足して学んだ時点（``score_timings``。3着以内は前日）なら S、
        能力スコア（T）を足して学んだ時点（``ability_score_timings``）なら T、トラックバイアスの補正（U）を足して学んだ時点（``track_bias_timings``）なら U、
        馬体重の表の割引（V）を足して学んだ時点（``weight_discount_timings``）なら V を足す。ほかの時点は無し。"""
        extras: list[DataAttachment] = []
        if timing in score_timings:
            extras.append(materials.score())
        if timing in ability_score_timings:
            extras.append(materials.ability_score())
        if timing in track_bias_timings:
            extras.append(materials.bias())
        if timing in weight_discount_timings:
            extras.append(materials.weight_discount())
        return extras

    def _place_price(self) -> PlacePriceEstimator | None:
        """学習のときに保存した複勝の見込みの倍率。無ければ（前の版で学習したモデル）None で、期待値は出さない。"""
        state = PlacePriceRepository(self._models).load()
        return PlacePriceEstimator.from_state(state) if state is not None else None
