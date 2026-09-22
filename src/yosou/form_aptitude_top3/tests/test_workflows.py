"""学習の流れ（設計書 05 の図1）と予測の流れ（図2）、モデルの保存と読み込み、コマンドの入口。"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from 共通 import db

from yosou.shared.dataset import HORSE_NO
from yosou.shared.evaluation import ENSEMBLE_NAME, TrainingReport
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import MEMBER_TYPES
from yosou.shared.repository import ModelRepository
from yosou.shared.repository.model_repository import SETTINGS_FILE
from yosou.shared.tests import synthetic_season as season

from ..command import CommandLine
from ..dataset import dataset_builder
from ..workflow import PROBABILITY, PredictionWorkflow


def test_training_saves_two_models_for_each_timing(trained: tuple[Path, TrainingReport]):
    models, report = trained
    expected_files = {SETTINGS_FILE, *(model_type.file_name for model_type in MEMBER_TYPES)}
    for timing in PredictionTiming:
        folder = models / timing.value
        assert report.model_folders[timing] == folder
        assert {path.name for path in folder.iterdir()} == expected_files


def test_training_saves_the_settings_it_used(trained: tuple[Path, TrainingReport]):
    models, _ = trained
    saved = json.loads((models / "race_day" / SETTINGS_FILE).read_text(encoding="utf-8"))
    # テスト用の設定ファイルに書いた値と、書かなかった項目の初期値
    assert saved["lightgbm"]["params"]["n_estimators"] == 60
    assert saved["lightgbm"]["params"]["num_leaves"] == 31


def test_training_reports_validation_scores(trained: tuple[Path, TrainingReport]):
    _, report = trained
    assert len(report.evaluations) == len(PredictionTiming) * (len(MEMBER_TYPES) + 1)
    ensembles = [e for e in report.evaluations if e.model == ENSEMBLE_NAME]
    # 合成のシーズンは能力の高い馬が上位に来やすいので、でたらめ（AUC 0.5）よりはっきり当たる
    assert all(e.auc > 0.65 and e.rows == len(report.split.valid) for e in ensembles)
    assert all(e.tree_count is None for e in ensembles)


def test_model_repository_reports_missing_models(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="train"):
        ModelRepository(tmp_path, MEMBER_TYPES).load(PredictionTiming.RACE_DAY)


def test_prediction_averages_the_two_models(season_db: Path, trained: tuple[Path, TrainingReport]):
    models, _ = trained
    with db.open_db(season_db) as con:
        workflow = PredictionWorkflow(
            dataset_builder(con), ModelRepository(models, MEMBER_TYPES),
        )
        prediction = workflow.run(season.CARD_RACE_ID, PredictionTiming.RACE_DAY)
    assert len(prediction) == 7 and season.SCRATCHED_HORSE_NO not in set(prediction[HORSE_NO])
    member_names = [model_type.name for model_type in MEMBER_TYPES]
    np.testing.assert_allclose(prediction[PROBABILITY], prediction[member_names].mean(axis=1))
    assert prediction[PROBABILITY].between(0, 1, inclusive="neither").all()


def _run_command(argv: list[str]) -> int:
    with pytest.raises(SystemExit) as stopped:
        CommandLine().run(argv)
    return stopped.value.code


def test_command_predicts_a_race_by_date_venue_and_number(season_db: Path, trained, capsys):
    models, _ = trained
    code = _run_command([
        "predict", "--date", "2025-01-11", "--venue", "東京", "--race", "2", "--timing", "木曜",
        "--db", str(season_db), "--models", str(models), "--format", "csv",
    ])
    lines = capsys.readouterr().out.strip().splitlines()
    assert code == 0 and len(lines) == 1 + 8
    assert lines[0] == f"順位,馬番,馬名,{PROBABILITY},LightGBM,CatBoost"


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
    assert (tmp_path / "models" / "thursday" / SETTINGS_FILE).exists()


def test_command_rejects_periods_out_of_order(season_db: Path, capsys):
    code = _run_command([
        "train", "--train-from", "2024-07-01", "--valid-from", "2024-01-01", "--db", str(season_db),
    ])
    assert code == 1 and "学習データの始まり" in capsys.readouterr().err


def test_command_reports_errors_in_one_line(season_db: Path, trained, capsys):
    models, _ = trained
    code = _run_command([
        "predict", season.JUMP_CARD_RACE_ID, "--timing", "当日",
        "--db", str(season_db), "--models", str(models),
    ])
    assert code == 1 and "障害レース" in capsys.readouterr().err
    assert _run_command(["predict", "--timing", "当日", "--db", str(season_db)]) == 1
