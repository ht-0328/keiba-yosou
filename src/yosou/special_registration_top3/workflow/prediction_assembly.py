"""この予想の決めごとを渡して、共通の ``PredictionWorkflow`` を組み立てる。"""

from __future__ import annotations

from pathlib import Path

import duckdb

from yosou.ability_score import RaceAbilityScoreAttacher
from yosou.shared.place_value import PlaceValueColumns
from yosou.shared.repository.speed_figure_repository import DEFAULT_FOLDER
from yosou.shared.workflow import ModelSegments, PredictionWorkflow, SegmentedPrediction

from ..dataset import NoOddsResolver, registration_dataset_builder
from .prediction_timings import WIN_FOLDER


def registration_prediction_workflow(con: duckdb.DuckDBPyConnection, models_root: Path,
                                     figure_folder: Path = DEFAULT_FOLDER) -> PredictionWorkflow:
    """登録馬の予測の流れ（設計書 05 の図2）。

    予測用データは ``registration_dataset_builder``（登録馬の行から）、オッズは決めない（``NoOddsResolver``）、複勝の期待値は出さない
    （``PlaceValueColumns(None)``。基準が無いので何も足さない）。3着以内のモデル（``models_root``）と1着のモデル（``models_root/1着``）の
    両方に、T（能力スコア）を足す関数（``RaceAbilityScoreAttacher``）を渡す。券種オッズなしのモデルと展開の予想は無い。
    """
    attach = RaceAbilityScoreAttacher().attach
    return PredictionWorkflow(
        registration_dataset_builder(con, figure_folder), SegmentedPrediction(ModelSegments(), models_root),
        NoOddsResolver(), PlaceValueColumns(None),
        win_predictor=SegmentedPrediction(ModelSegments(), models_root / WIN_FOLDER),
        extras=[attach], win_extras=[attach],
    )
