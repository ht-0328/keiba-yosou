"""学習の流れ・予測の流れ・評価のコマンド（設計書 05 の図1・図2・16）。"""

from __future__ import annotations

import argparse
from pathlib import Path

from 共通 import db

from yosou.shared.evaluation import TrainingReport
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import MEMBER_TYPES
from yosou.shared.place_value import PlacePriceEstimator, PlaceValueColumns
from yosou.shared.repository import AnnouncedOddsRepository, PlacePriceRepository
from yosou.shared.workflow import ModelSegments, SegmentedPrediction
from yosou.shared.tests import synthetic_season as season
from yosou.shared.tests.synthetic_season.season_plan import FIELD_SIZE

from ..command import EvaluateCommand
from ..dataset import OddsResolver, dataset_builder
from ..workflow import PROBABILITY, PredictionWorkflow
from .test_dataset_builder import FINISHED_STAKES_RID


def test_training_saves_models_for_each_timing(trained: tuple[Path, TrainingReport]):
    models, report = trained
    for timing in PredictionTiming:
        folder = models / timing.name.lower()
        for member_type in MEMBER_TYPES:
            assert (folder / member_type.file_name).exists()
    assert len(report.evaluations) > 0


def test_prediction_workflow_scores_a_finished_stakes_race(trained: tuple[Path, TrainingReport], season_db: Path):
    models, _ = trained
    with db.open_db(season_db) as con:
        state = PlacePriceRepository(models).load()
        estimator = PlacePriceEstimator.from_state(state) if state is not None else None
        workflow = PredictionWorkflow(
            dataset_builder(con), SegmentedPrediction(ModelSegments(), models),
            OddsResolver(AnnouncedOddsRepository(con)), PlaceValueColumns(estimator),
        )
        prediction = workflow.run(FINISHED_STAKES_RID, PredictionTiming.RACE_DAY)
    assert len(prediction) == FIELD_SIZE
    assert prediction[PROBABILITY].between(0.0, 1.0).all()


def test_evaluate_command_reports_value_bands_and_favorite_tables(trained: tuple[Path, TrainingReport],
                                                                  season_db: Path):
    models, _ = trained
    args = argparse.Namespace(
        db=season_db, models=models, format="markdown", out=None,
        timing=PredictionTiming.RACE_DAY, warmup_from=season.FIRST_RACE_DAY,
        train_from=season.TRAIN_FIRST_DAY, valid_from=season.VALID_FIRST_DAY, test_from=season.TEST_FIRST_DAY,
    )
    tables = EvaluateCommand().run(args)
    titles = [table.title for table in tables]
    assert any("期待値の帯" in title for title in titles)
    assert any("本命と1番人気" in title for title in titles)
