"""学習の流れ（設計書 05 の図1）と予測の流れ（図2）、モデルの保存と読み込み、コマンドの入口。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from 共通 import db

from yosou.shared.dataset import HORSE_NO, RACE_ID, PopularityApplier, PopularityInput, TrainingData
from yosou.shared.evaluation import ENSEMBLE_NAME, TrainingReport
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import MEMBER_TYPES
from yosou.shared.repository import AnnouncedOddsRepository, ModelRepository
from yosou.shared.repository.model_repository import SETTINGS_FILE
from yosou.shared.tests import synthetic_season as season

from ..command import CommandLine
from ..dataset import dataset_builder
from ..workflow import PROBABILITY, TIMINGS, PredictionWorkflow

#: 確定前の 1R（8頭登録・馬番8 は速報で取消）で、利用者が渡す人気。7頭立てなので 1〜3番人気が対象。
GIVEN_POPULARITY = ["3:1", "5:2", "1:3"]


def _workflow(con, models: Path) -> PredictionWorkflow:
    return PredictionWorkflow(
        dataset_builder(con), ModelRepository(models, MEMBER_TYPES),
        PopularityApplier(AnnouncedOddsRepository(con)),
    )


def test_training_saves_two_models_for_the_two_timings(trained: tuple[Path, TrainingReport]):
    models, report = trained
    expected_files = {SETTINGS_FILE, *(model_type.file_name for model_type in MEMBER_TYPES)}
    assert set(report.model_folders) == set(TIMINGS)
    for timing in TIMINGS:
        folder = models / timing.value
        assert report.model_folders[timing] == folder
        assert {path.name for path in folder.iterdir()} == expected_files
    # 木曜は学習しない（設計書 07）
    assert not (models / PredictionTiming.THURSDAY.value).exists()


def test_training_reports_validation_scores(trained: tuple[Path, TrainingReport]):
    _, report = trained
    assert len(report.evaluations) == len(TIMINGS) * (len(MEMBER_TYPES) + 1)
    ensembles = [e for e in report.evaluations if e.model == ENSEMBLE_NAME]
    assert all(e.rows == len(report.split.valid) for e in ensembles)
    assert all(0.0 < e.log_loss for e in ensembles)


def test_prediction_of_a_finished_race_uses_the_final_popularity(
        season_db: Path, trained: tuple[Path, TrainingReport], training_data: TrainingData):
    models, _ = trained
    race_id = training_data.ids[RACE_ID].iloc[-1]
    with db.open_db(season_db) as con:
        prediction = _workflow(con, models).run(race_id, PredictionTiming.RACE_DAY)
    # 10頭立てなので 1〜3番人気の3頭。--pops を渡さなくても、元DB の確定単勝人気で選べる
    assert prediction["人気順位"].tolist() == [1.0, 2.0, 3.0]
    member_names = [model_type.name for model_type in MEMBER_TYPES]
    np.testing.assert_allclose(prediction[PROBABILITY], prediction[member_names].mean(axis=1))
    assert prediction[PROBABILITY].between(0, 1, inclusive="neither").all()


def test_prediction_of_a_card_needs_the_given_popularity(season_db: Path, trained):
    models, _ = trained
    given = PopularityInput.of(GIVEN_POPULARITY)
    with db.open_db(season_db) as con:
        prediction = _workflow(con, models).run(season.CARD_RACE_ID, PredictionTiming.RACE_DAY, given)
        with pytest.raises(ValueError, match="--pops"):
            _workflow(con, models).run(season.CARD_RACE_ID, PredictionTiming.RACE_DAY)
    assert prediction[HORSE_NO].tolist() == [1, 3, 5]
    assert prediction["人気順位"].tolist() == [3.0, 1.0, 2.0]


def test_prediction_is_not_offered_on_thursday(season_db: Path, trained):
    models, _ = trained
    with db.open_db(season_db) as con, pytest.raises(ValueError, match="前日・当日"):
        _workflow(con, models).run(season.CARD_RACE_ID, PredictionTiming.THURSDAY)


def test_model_repository_reports_missing_models(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="train"):
        ModelRepository(tmp_path, MEMBER_TYPES).load(PredictionTiming.DAY_BEFORE)


def _run_command(argv: list[str]) -> int:
    with pytest.raises(SystemExit) as stopped:
        CommandLine().run(argv)
    return stopped.value.code


def test_command_predicts_a_card_with_the_given_popularity(season_db: Path, trained, capsys):
    models, _ = trained
    code = _run_command([
        "predict", season.CARD_RACE_ID, "--timing", "当日", "--pops", *GIVEN_POPULARITY,
        "--db", str(season_db), "--models", str(models), "--format", "csv",
    ])
    lines = capsys.readouterr().out.strip().splitlines()
    assert code == 0 and len(lines) == 1 + 3
    assert lines[0] == f"順位,馬番,馬名,人気順位,{PROBABILITY},LightGBM,CatBoost"


def test_command_reads_the_popularity_written_with_commas(season_db: Path, trained, capsys):
    models, _ = trained
    code = _run_command([
        "predict", season.CARD_RACE_ID, "--timing", "前日", "--pops", ",".join(GIVEN_POPULARITY),
        "--db", str(season_db), "--models", str(models), "--format", "csv",
    ])
    assert code == 0 and len(capsys.readouterr().out.strip().splitlines()) == 1 + 3


def test_command_rejects_thursday(season_db: Path, trained, capsys):
    models, _ = trained
    code = _run_command([
        "predict", season.CARD_RACE_ID, "--timing", "木曜", "--pops", *GIVEN_POPULARITY,
        "--db", str(season_db), "--models", str(models),
    ])
    assert code == 1 and "前日・当日" in capsys.readouterr().err


def test_command_reports_errors_in_one_line(season_db: Path, trained, capsys):
    models, _ = trained
    code = _run_command([
        "predict", season.JUMP_CARD_RACE_ID, "--timing", "当日",
        "--db", str(season_db), "--models", str(models),
    ])
    assert code == 1 and "障害レース" in capsys.readouterr().err
    assert _run_command(["predict", "--timing", "当日", "--db", str(season_db)]) == 1


def test_command_trains_and_writes_the_report(season_db: Path, fast_settings_path: Path, tmp_path: Path):
    out = tmp_path / "report.md"
    code = _run_command([
        "train", "--config", str(fast_settings_path), "--warmup-from", "2023-10-07",
        "--train-from", "2024-01-01", "--valid-from", "2024-07-01", "--test-from", "2024-10-01",
        "--db", str(season_db), "--models", str(tmp_path / "models"), "--out", str(out),
    ])
    text = out.read_text(encoding="utf-8")
    assert code == 0 and "検証データでの当たり具合" in text and "保存したモデル" in text
    assert "| ウォームアップ | 2023-10-07 | 2023-12-31 |" in text
    assert (tmp_path / "models" / "day_before" / SETTINGS_FILE).exists()
    assert not (tmp_path / "models" / "thursday").exists()
