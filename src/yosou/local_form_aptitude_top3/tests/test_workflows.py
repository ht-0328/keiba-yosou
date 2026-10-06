"""学習の流れ（設計書 05 の図1）・予測の流れ（図2）・テスト期間の確かめ（図4）と、コマンドの入口。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from 印の成績.prediction_file import PredictionFile

from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import MEMBER_TYPES
from yosou.shared.repository.model_repository import SETTINGS_FILE
from yosou.shared.workflow import FIELD_SHARE_NAME, MARKET_NAME, PROBABILITY, WIN_PROBABILITY
from yosou.shared.tests import local_season as season

from ..command import CommandLine
from ..workflow import POOL_FREE_FOLDER, TIMING_LABELS, WIN_FOLDER
from .test_dataset_builder import CARD_ODDS

#: 出馬表のレースに手で渡す単勝オッズ（``--odds`` の書き方）。
CARD_ODDS_TEXTS = [f"{horse_no}:{odds}" for horse_no, odds in CARD_ODDS.items()]


def _run_command(argv: list[str]) -> int:
    with pytest.raises(SystemExit) as stopped:
        CommandLine().run(argv)
    return stopped.value.code


def test_training_saves_two_models_for_each_timing(trained: tuple[Path, str]):
    models, _ = trained
    expected_files = {SETTINGS_FILE, *(model_type.file_name for model_type in MEMBER_TYPES)}
    for timing in PredictionTiming:
        assert {path.name for path in (models / timing.value).iterdir()} == expected_files
        assert {path.name for path in (models / WIN_FOLDER / timing.value).iterdir()} == expected_files
    assert {path.name for path in (models / POOL_FREE_FOLDER / "race_day").iterdir()} == expected_files
    assert {path.name for path in (models / POOL_FREE_FOLDER / WIN_FOLDER / "race_day").iterdir()} == expected_files


def test_training_report_names_the_first_timing_as_entry_list(trained: tuple[Path, str]):
    _, text = trained
    assert "| 出馬表 |" in text and "| 木曜 |" not in text
    for subject in ("今の材料", "券種オッズなし"):
        assert f"{subject}: 検証データでの当たり具合" in text and f"1着: {subject}: 保存したモデル" in text
    assert "複勝の見込みの倍率" in text


def test_command_predicts_the_entry_list_timing_without_odds(local_season_db: Path, trained, capsys):
    models, _ = trained
    code = _run_command([
        "predict", "--date", "2025-01-11", "--venue", "大井", "--race", "2", "--timing", "出馬表",
        "--db", str(local_season_db), "--models", str(models), "--format", "csv",
    ])
    lines = capsys.readouterr().out.strip().splitlines()
    assert code == 0 and len(lines) == 1 + 8
    assert lines[0] == f"順位,馬番,馬名,{WIN_PROBABILITY},{PROBABILITY},LightGBM,CatBoost"


def test_command_shows_the_odds_it_used_on_race_day(local_season_db: Path, trained, capsys):
    models, _ = trained
    code = _run_command([
        "predict", season.CARD_RACE_ID, "--timing", "当日", "--odds", *CARD_ODDS_TEXTS,
        "--db", str(local_season_db), "--models", str(models), "--format", "markdown",
    ])
    out = capsys.readouterr().out
    assert code == 0 and f"{TIMING_LABELS[PredictionTiming.RACE_DAY]}の時点" in out
    # 取消の馬番8 を除いた7頭。単勝オッズ・期待値の列が出る
    assert out.count("| ウマ") == 7 and "単勝オッズ" in out and "単勝の期待値" in out


def test_command_asks_for_odds_when_the_database_has_none(local_season_db: Path, trained, capsys):
    models, _ = trained
    code = _run_command(["predict", season.PLAIN_CARD_RACE_ID, "--timing", "前日", "--db", str(local_season_db), "--models", str(models)])
    assert code == 1 and "--odds" in capsys.readouterr().err


def test_backtest_compares_with_the_market_and_writes_prediction_files(local_season_db: Path, trained, tmp_path: Path, capsys):
    models, _ = trained
    predictions = tmp_path / "predictions"
    code = _run_command([
        "backtest", "--warmup-from", season.FIRST_RACE_DAY.isoformat(), "--train-from", season.TRAIN_FIRST_DAY.isoformat(),
        "--valid-from", season.VALID_FIRST_DAY.isoformat(), "--test-from", season.TEST_FIRST_DAY.isoformat(),
        "--db", str(local_season_db), "--models", str(models), "--predictions", str(predictions),
    ])
    out = capsys.readouterr().out
    assert code == 0
    assert "テスト期間での当たり具合: 3着以内" in out and "テスト期間での当たり具合: 1着" in out
    assert MARKET_NAME in out and FIELD_SHARE_NAME in out and "| 出馬表 |" in out
    # 時点ごとに、3着以内と1着の予測の表を書く。道具「印の成績」が読める形
    for timing in PredictionTiming:
        assert (predictions / f"{timing.value}.pkl").exists() and (predictions / f"{timing.value}-1着.pkl").exists()
    table = PredictionFile(str(predictions / "day_before.pkl")).load()
    assert {"race_id", "race_date", "horse_id", "horse_no", "probability", "period", "probability_lightgbm", "probability_catboost"} <= set(table.columns)
    assert set(table["period"]) == {"テスト"} and pd.to_datetime(table["race_date"]).min() >= pd.Timestamp(season.TEST_FIRST_DAY)


def test_command_rejects_periods_out_of_order(local_season_db: Path, capsys):
    code = _run_command(["train", "--train-from", "2024-07-01", "--valid-from", "2024-01-01", "--db", str(local_season_db)])
    assert code == 1 and "学習データの始まり" in capsys.readouterr().err
