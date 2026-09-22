"""学習の流れ（設計書 05 の図1）と予測の流れ（図2）、モデルの保存と読み込み、コマンドの入口。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pytest

from 共通 import db

from yosou.shared.dataset import OddsInput, OddsResolver
from yosou.shared.evaluation import ENSEMBLE_NAME, ClassEvaluation, TrainingReport
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import CLASS_MEMBER_TYPES
from yosou.shared.repository import AnnouncedOddsRepository
from yosou.shared.repository.model_repository import SETTINGS_FILE
from yosou.shared.tests import synthetic_season as season

from ..command import CommandLine
from ..dataset import BetType, UpsetLevel, race_dataset_builder
from ..evaluation import UserRuleBaseline
from ..workflow import BET, PREDICTION_COLUMNS, TOP_LEVEL, UPSET_OR_MORE, PredictionWorkflow, model_repositories
from .conftest import TRAINED_BETS
from .test_dataset_builder import CARD_ODDS

#: 出馬表のレースに手で渡す単勝オッズ（``--odds`` の書き方）。
CARD_ODDS_TEXTS = [f"{horse_no}:{odds}" for horse_no, odds in CARD_ODDS.items()]


def test_training_saves_two_models_for_each_bet_and_timing(trained: tuple[Path, dict[BetType, TrainingReport]]):
    models, reports = trained
    expected_files = {SETTINGS_FILE, *(model_type.file_name for model_type in CLASS_MEMBER_TYPES)}
    for bet in TRAINED_BETS:
        for timing in PredictionTiming:
            folder = models / bet.key / timing.value
            assert reports[bet].model_folders[timing] == folder
            assert {path.name for path in folder.iterdir()} == expected_files


def test_training_reports_multiclass_scores(trained: tuple[Path, dict[BetType, TrainingReport]]):
    _, reports = trained
    for bet in TRAINED_BETS:
        report = reports[bet]
        assert report.split.train.label_name == bet.column_name
        assert len(report.evaluations) == len(PredictionTiming) * (len(CLASS_MEMBER_TYPES) + 1)
        ensembles = [e for e in report.evaluations if e.model == ENSEMBLE_NAME]
        assert all(isinstance(e, ClassEvaluation) and e.tree_count is None for e in ensembles)
        for evaluation in ensembles:
            assert 0 <= evaluation.accuracy <= 1 and 0 <= evaluation.macro_f1 <= 1
            assert len(evaluation.cumulative_auc) == 3 and len(evaluation.confusion_matrix) == 4
            assert sum(sum(row) for row in evaluation.confusion_matrix) == evaluation.rows


def test_user_rule_baseline_measures_precision_and_recall(training_data):
    result = UserRuleBaseline().evaluate(training_data.with_label(BetType.TRIFECTA.column_name))
    assert result.rows > 0 and 0 <= result.hits <= result.rows and 0 <= result.base_rate <= 1
    assert np.isnan(result.precision) or 0 <= result.precision <= 1


def _workflow(con: duckdb.DuckDBPyConnection, models: Path) -> PredictionWorkflow:
    return PredictionWorkflow(
        race_dataset_builder(con), model_repositories(models), OddsResolver(AnnouncedOddsRepository(con)),
    )


def test_prediction_returns_one_row_per_bet_with_probabilities_summing_to_one(
        season_db: Path, trained: tuple[Path, dict[BetType, TrainingReport]]):
    models, _ = trained
    with db.open_db(season_db) as con:
        prediction = _workflow(con, models).run(
            season.CARD_RACE_ID, PredictionTiming.RACE_DAY, OddsInput.of(CARD_ODDS_TEXTS), TRAINED_BETS)
    assert prediction[BET].tolist() == [bet.label for bet in TRAINED_BETS]
    assert list(prediction.columns)[-len(PREDICTION_COLUMNS):] == list(PREDICTION_COLUMNS)
    levels = list(UpsetLevel.labels())
    np.testing.assert_allclose(prediction[levels].sum(axis=1), 1.0)
    np.testing.assert_allclose(prediction[UPSET_OR_MORE], 1.0 - prediction["固い"])
    assert (prediction[TOP_LEVEL] == prediction[levels].idxmax(axis=1)).all()


def test_thursday_prediction_needs_no_odds(season_db: Path, trained: tuple[Path, dict[BetType, TrainingReport]]):
    models, _ = trained
    with db.open_db(season_db) as con:
        prediction = _workflow(con, models).run(season.ENTRY_LIST_RACE_ID, PredictionTiming.THURSDAY, bets=TRAINED_BETS)
    assert len(prediction) == len(TRAINED_BETS)


def _run_command(argv: list[str]) -> int:
    with pytest.raises(SystemExit) as stopped:
        CommandLine().run(argv)
    return stopped.value.code


def test_command_predicts_a_race_by_date_venue_and_number(season_db: Path, trained, capsys):
    models, _ = trained
    code = _run_command([
        "predict", "--date", "2025-01-11", "--venue", "東京", "--race", "2", "--timing", "木曜",
        "--bet", *(bet.label for bet in TRAINED_BETS),
        "--db", str(season_db), "--models", str(models), "--format", "csv",
    ])
    lines = capsys.readouterr().out.strip().splitlines()
    assert code == 0 and len(lines) == 1 + len(TRAINED_BETS)
    assert lines[0] == ",".join(PREDICTION_COLUMNS)


def test_command_asks_for_odds_when_the_database_has_none(season_db: Path, trained, capsys):
    models, _ = trained
    code = _run_command([
        "predict", season.CARD_RACE_ID, "--timing", "当日", "--bet", "単勝",
        "--db", str(season_db), "--models", str(models),
    ])
    assert code == 1 and "--odds" in capsys.readouterr().err


def test_command_reports_missing_models(season_db: Path, trained, capsys):
    models, _ = trained
    code = _run_command([
        "predict", season.CARD_RACE_ID, "--timing", "当日", "--odds", *CARD_ODDS_TEXTS, "--bet", "馬連",
        "--db", str(season_db), "--models", str(models),
    ])
    assert code == 1 and "train" in capsys.readouterr().err


def test_command_trains_one_bet_and_writes_the_report(season_db: Path, fast_settings_path: Path, tmp_path: Path):
    out = tmp_path / "report.md"
    code = _run_command([
        "train", "--bet", "3連単", "--config", str(fast_settings_path), "--warmup-from", "2023-10-07",
        "--train-from", "2024-01-01", "--valid-from", "2024-07-01", "--test-from", "2024-10-01",
        "--db", str(season_db), "--models", str(tmp_path / "models"), "--out", str(out),
    ])
    text = out.read_text(encoding="utf-8")
    assert code == 0 and "3連単: 検証データでの当たり具合" in text and "混同行列" in text
    assert "利用者の規則" in text and "| ウォームアップ | 2023-10-07 | 2023-12-31 |" in text
    assert (tmp_path / "models" / "trifecta" / "thursday" / SETTINGS_FILE).exists()
    assert not (tmp_path / "models" / "win").exists()


def test_command_reports_errors_in_one_line(season_db: Path, trained, capsys):
    models, _ = trained
    code = _run_command([
        "predict", season.JUMP_CARD_RACE_ID, "--timing", "当日", "--db", str(season_db), "--models", str(models),
    ])
    assert code == 1 and "障害レース" in capsys.readouterr().err
