"""学習の流れ・予測の流れ・評価のコマンド（設計書 05 の図1・図2・16）。"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pytest

from 共通 import db

from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.odds import TOP3_RATE
from yosou.shared.ml_model import MEMBER_TYPES
from yosou.shared.place_value import PLACE_VALUE, PlacePriceEstimator, PlaceValueColumns
from yosou.shared.repository import AnnouncedOddsRepository, PlacePriceRepository
from yosou.shared.repository.model_repository import SETTINGS_FILE
from yosou.shared.tests.synthetic_season.season_plan import FIELD_SIZE
from yosou.shared.workflow import AVERAGE, ModelSegments, SegmentedPrediction
from yosou.shared.tests import synthetic_season as season

from ..command import CommandLine, EvaluateCommand, PredictCommand
from ..dataset import POOL_FREE_FOLDER, OddsResolver, PoolAvailability, PoolFreeData, ability_dataset_builder, race_day_dataset_builder
from ..feature import WIN_ODDS
from ..workflow import PROBABILITY, PredictionWorkflow
from .test_dataset_builder import FINISHED_STAKES_RID, FLAT_RID


def test_training_saves_models_for_each_timing_and_the_pool_free_model(trained: tuple[Path, str]):
    models, text = trained
    expected_files = {SETTINGS_FILE, *(member_type.file_name for member_type in MEMBER_TYPES)}
    for timing in PredictionTiming:
        assert {path.name for path in (models / timing.value).iterdir()} == expected_files
    # 当日に券種のオッズが無いレースのための、券種の支持を使わないモデルも置く
    assert {path.name for path in (models / POOL_FREE_FOLDER / "race_day").iterdir()} == expected_files
    for subject in ("当日の材料＋重賞の傾向", "券種オッズなし", "馬の力の材料＋重賞の傾向"):
        assert f"{subject}: 検証データでの当たり具合" in text and f"{subject}: 保存したモデル" in text
    assert "複勝の見込みの倍率" in text and PlacePriceRepository(models).load() is not None


def _workflow(con, models: Path, figure_cache: Path, timing: PredictionTiming) -> PredictionWorkflow:
    """その時点の予測の流れ（木曜・前日は馬の力の材料＋K、当日は当日の材料＋K。券種のオッズが無ければ券種オッズなしに切り替える）。"""
    builder = ability_dataset_builder if timing is not PredictionTiming.RACE_DAY else race_day_dataset_builder
    state = PlacePriceRepository(models).load()
    estimator = PlacePriceEstimator.from_state(state) if state is not None else None
    return PredictionWorkflow(
        builder(con, figure_cache), SegmentedPrediction(ModelSegments(), models),
        OddsResolver(AnnouncedOddsRepository(con)), PlaceValueColumns(estimator),
        pool_free=SegmentedPrediction(ModelSegments(), models / POOL_FREE_FOLDER),
    )


def test_race_day_prediction_uses_the_pool_free_models_when_the_pool_odds_are_missing(trained: tuple[Path, str], season_db: Path,
                                                                                     figure_cache: Path):
    models, _ = trained
    with db.open_db(season_db) as con:
        prediction = _workflow(con, models, figure_cache, PredictionTiming.RACE_DAY).run(FINISHED_STAKES_RID, PredictionTiming.RACE_DAY)
        data = race_day_dataset_builder(con, figure_cache).build_prediction_data(FINISHED_STAKES_RID, PredictionTiming.RACE_DAY)
    assert len(prediction) == FIELD_SIZE and prediction[PROBABILITY].between(0.0, 1.0).all()
    assert {WIN_ODDS, TOP3_RATE, PLACE_VALUE} <= set(prediction.columns)
    # 合成DB には券種のオッズが無いので、券種の支持を外して、券種の支持を使わないモデルで予測する
    assert PoolAvailability().missing(data)
    expected = SegmentedPrediction(ModelSegments(), models / POOL_FREE_FOLDER).predict(PoolFreeData().prediction(data))
    np.testing.assert_allclose(prediction[PROBABILITY].to_numpy(), expected[AVERAGE].to_numpy())


def test_thursday_prediction_has_no_odds_column(trained: tuple[Path, str], season_db: Path, figure_cache: Path):
    models, _ = trained
    with db.open_db(season_db) as con:
        prediction = _workflow(con, models, figure_cache, PredictionTiming.THURSDAY).run(FINISHED_STAKES_RID, PredictionTiming.THURSDAY)
    assert len(prediction) == FIELD_SIZE and WIN_ODDS not in prediction.columns and PLACE_VALUE not in prediction.columns


def _run_command(argv: list[str]) -> int:
    with pytest.raises(SystemExit) as stopped:
        CommandLine().run(argv)
    return stopped.value.code


def test_command_predicts_a_finished_stakes_race(trained: tuple[Path, str], season_db: Path, figure_cache: Path, capsys):
    models, _ = trained
    code = _run_command([
        "predict", FINISHED_STAKES_RID, "--timing", "前日", "--figure-cache", str(figure_cache),
        "--db", str(season_db), "--models", str(models), "--format", "csv",
    ])
    lines = capsys.readouterr().out.strip().splitlines()
    assert code == 0 and len(lines) == 1 + FIELD_SIZE and lines[0].startswith("順位,馬番,馬名,")


def test_tables_say_the_model_is_retired(trained: tuple[Path, str], season_db: Path, figure_cache: Path):
    """引退したことが、学習と予測の結果の表に出る（動きは変えない）。"""
    models, text = trained
    assert "【引退】" in text
    with db.open_db(season_db) as con:
        table = PredictCommand().predict_table(con, FINISHED_STAKES_RID, PredictionTiming.RACE_DAY, models, figure_cache=figure_cache)
    assert table.note.startswith("【引退】")


def test_command_rejects_non_stakes_races_in_one_line(trained: tuple[Path, str], season_db: Path, figure_cache: Path, capsys):
    models, _ = trained
    code = _run_command([
        "predict", FLAT_RID, "--timing", "当日", "--figure-cache", str(figure_cache), "--db", str(season_db), "--models", str(models),
    ])
    assert code == 1 and "重賞" in capsys.readouterr().err


def test_evaluate_command_reports_value_bands_and_favorite_tables(trained: tuple[Path, str], season_db: Path, figure_cache: Path):
    models, _ = trained
    args = argparse.Namespace(
        db=season_db, models=models, format="markdown", out=None, figure_cache=figure_cache,
        timing=PredictionTiming.RACE_DAY, warmup_from=season.FIRST_RACE_DAY,
        train_from=season.TRAIN_FIRST_DAY, valid_from=season.VALID_FIRST_DAY, test_from=season.TEST_FIRST_DAY,
    )
    tables = EvaluateCommand().run(args)
    titles = [table.title for table in tables]
    assert any("期待値の帯" in title for title in titles)
    assert any("本命と1番人気" in title for title in titles)
