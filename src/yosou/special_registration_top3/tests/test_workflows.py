"""学習の流れ（設計書 05 の図1）、予測（図2）、7つの区切りでの確かめ（図5）、登録馬の確かめ（図6）、コマンドの入口。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from 共通 import db

from yosou.shared.dataset import HORSE_ID, RACE_ID
from yosou.shared.ml_model import MEMBER_TYPES
from yosou.shared.repository.model_repository import SETTINGS_FILE
from yosou.shared.tests import synthetic_season as season
from yosou.shared.tests.synthetic_season.season_plan import STAKES_RACE
from yosou.shared.workflow.backtest_workflow import PREDICTION_COLUMNS

from ..command import SUBJECT, CommandLine
from ..dataset import registration_dataset_builder
from ..feature import CATALOG, FIELD_COMPARISON_NAMES
from ..workflow import (
    FILE_NAME,
    NO_FIELD_COMPARISON,
    PROBABILITY,
    RAN,
    WIN_FOLDER,
    WIN_PROBABILITY,
    WindowedBacktestWorkflow,
    registration_prediction_workflow,
    windows_named,
)
from ..workflow.prediction_timings import REGISTRATION_TIMING

#: 架空のシーズンで回せる区切り（検証 2024年1〜6月・テスト 2024年7〜12月）。
_WINDOW = "2024年後半"


def _run(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as stopped:
        CommandLine().run(argv)
    assert stopped.value.code == 0


def test_training_saves_top3_and_win_models_for_the_registration_timing(trained: tuple[Path, str]):
    models, text = trained
    expected_files = {SETTINGS_FILE, *(model_type.file_name for model_type in MEMBER_TYPES)}
    assert {path.name for path in (models / REGISTRATION_TIMING.value).iterdir()} == expected_files
    assert {path.name for path in (models / WIN_FOLDER / REGISTRATION_TIMING.value).iterdir()} == expected_files
    # 3着以内と1着の学習の結果を、時点の表示名「特別登録」で出す
    assert f"{SUBJECT}: 検証データでの当たり具合" in text and f"1着: {SUBJECT}: 検証データでの当たり具合" in text
    assert "特別登録" in text and "複勝の見込みの倍率" not in text


def test_prediction_covers_every_registered_horse_with_t_attached(trained: tuple[Path, str], season_db: Path, figure_cache: Path):
    models, _ = trained
    with db.open_db(season_db) as con:
        workflow = registration_prediction_workflow(con, models, figure_cache)
        prediction = workflow.run(season.REGISTRATION_ONLY_RACE_ID, REGISTRATION_TIMING)
        explained = workflow.explain(season.REGISTRATION_ONLY_RACE_ID, REGISTRATION_TIMING)
    assert len(prediction) == season.REGISTRATION_ONLY_FIELD_SIZE
    assert prediction[PROBABILITY].between(0, 1).all() and prediction[WIN_PROBABILITY].between(0, 1).all()
    # モデルに渡した特徴量は 180個（T を足したもの）。馬番は無い
    assert list(explained.features.columns) == list(CATALOG.names)
    assert prediction[HORSE_ID].notna().all()


def test_predict_command_outputs_a_table_per_race(trained: tuple[Path, str], season_db: Path, figure_cache: Path, tmp_path: Path):
    models, _ = trained
    out = tmp_path / "predict.md"
    _run(["predict", "--date", season.FUTURE_DAY.isoformat(), "--all", "--figure-cache", str(figure_cache),
          "--db", str(season_db), "--models", str(models), "--out", str(out)])
    text = out.read_text(encoding="utf-8")
    assert text.count("の予測: 特別登録の時点") == 2 and "出走すれば3着以内に入る確率" in text and "地方" in text
    assert "馬番" not in text
    with pytest.raises(SystemExit) as stopped:
        CommandLine().run(["predict", season.CARD_RACE_ID, "--figure-cache", str(figure_cache), "--db", str(season_db), "--models", str(models)])
    assert stopped.value.code == 1


def test_windowed_backtest_trains_each_window_and_writes_predictions_with_the_window(
        season_db: Path, figure_cache: Path, fast_settings_path: Path, tmp_path: Path):
    windows = windows_named([_WINDOW])
    with db.open_db(season_db) as con:
        data = registration_dataset_builder(con, figure_cache).build_training_data(windows[0].period(season.FIRST_RACE_DAY, date(2023, 11, 1)))
    workflow = WindowedBacktestWorkflow(tmp_path / "models", tmp_path / "predictions", fast_settings_path,
                                        season.FIRST_RACE_DAY, date(2023, 11, 1), variant=NO_FIELD_COMPARISON)
    result = workflow.run(data, windows)
    assert result.feature_count == len(CATALOG.names) - len(FIELD_COMPARISON_NAMES)
    for label, rows in result.special.items():
        names = [name for name, _ in rows]
        assert names == [_WINDOW]
        models = {evaluation.model for evaluation in rows[0][1]}
        assert "頭数から見た割合" in models and "平均（アンサンブル）" in models
    for label, path in result.prediction_paths.items():
        table = pd.read_pickle(path)
        assert list(table.columns)[:len(PREDICTION_COLUMNS)] == list(PREDICTION_COLUMNS)
        assert set(table[PREDICTION_COLUMNS[5]]) == {_WINDOW} and NO_FIELD_COMPARISON in path.name
        # 書くのは特別競走の行だけ（架空のシーズンの特別競走は月の最初の土曜の重賞。レース番号 06）
        assert len(table) > 0 and table[PREDICTION_COLUMNS[0]].astype(str).str.endswith(STAKES_RACE.race_no).all()
    assert (tmp_path / "models" / _WINDOW / REGISTRATION_TIMING.value / SETTINGS_FILE).exists()
    assert (tmp_path / "models" / _WINDOW / WIN_FOLDER / REGISTRATION_TIMING.value / SETTINGS_FILE).exists()


def test_registrations_command_checks_every_registered_horse(trained: tuple[Path, str], season_db: Path, figure_cache: Path, tmp_path: Path):
    models, _ = trained
    out = tmp_path / "registrations.md"
    _run(["registrations", "--from", season.FUTURE_DAY.isoformat(), "--to", season.FUTURE_DAY.isoformat(),
          "--predictions", str(tmp_path), "--figure-cache", str(figure_cache), "--db", str(season_db),
          "--models", str(models), "--out", str(out)])
    table = pd.read_pickle(tmp_path / FILE_NAME)
    # 2R の9頭と 4R の8頭。印は付けない。まだ終わっていないので出走したは偽
    assert len(table) == season.FUTURE_FIELD_SIZE + 1 + season.REGISTRATION_ONLY_FIELD_SIZE
    assert "印" not in table.columns and table[RACE_ID].nunique() == 2
    assert not table[RAN].any()
    text = out.read_text(encoding="utf-8")
    assert "確かめた登録馬" in text and "出走した登録馬だけでの当たり具合" in text and "出走しなかった登録馬の割合" not in text
