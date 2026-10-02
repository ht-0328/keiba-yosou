"""この予想のテストの準備。実DB は使わず、合成DB（架空の1シーズン）だけを使う。

架空の1シーズンには、月の最初の土曜だけ行う重賞「テスト記念」（G3・特別競走番号 9001・6R）があり、
この予想はその出走だけを学習データにする。合成DB（``season_db``）・速い設定（``fast_settings_path``）・期間（``season_period``）は
``src/yosou/conftest.py``。

| フィクスチャ | 中身 |
|---|---|
| ``figure_cache`` | スピード指数をとっておく一時フォルダ（本物の ``reports/能力指数/cache/`` を書き換えない） |
| ``ability_training_data`` | 木曜・前日のモデルの学習データ（重賞の出走だけ・M・J・K） |
| ``race_day_training_data`` | 当日のモデルの学習データ（重賞の出走だけ・手本の当日の材料に K を足した 295個） |
| ``trained`` | 本番と同じ学習（train コマンド）を1回通した結果（モデルを置いたフォルダと、学習の報告の文章） |
"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import db

from yosou.shared.dataset import TrainingData, TrainingPeriod
from yosou.shared.tests import synthetic_season as season

from ..command import CommandLine
from ..dataset import ability_dataset_builder, race_day_dataset_builder


@pytest.fixture(scope="session")
def figure_cache(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """スピード指数をとっておく一時フォルダ。"""
    return tmp_path_factory.mktemp("figures")


@pytest.fixture(scope="session")
def ability_training_data(season_db: Path, season_period: TrainingPeriod, figure_cache: Path) -> TrainingData:
    """架空の1シーズンの、木曜・前日のモデルの学習データ（重賞だけ）。"""
    with db.open_db(season_db) as con:
        return ability_dataset_builder(con, figure_cache).build_training_data(season_period)


@pytest.fixture(scope="session")
def race_day_training_data(season_db: Path, season_period: TrainingPeriod, figure_cache: Path) -> TrainingData:
    """架空の1シーズンの、当日のモデルの学習データ（重賞だけ）。"""
    with db.open_db(season_db) as con:
        return race_day_dataset_builder(con, figure_cache).build_training_data(season_period)


@pytest.fixture(scope="session")
def trained(season_db: Path, fast_settings_path: Path, figure_cache: Path,
            tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str]:
    """train コマンドを1回通して、モデルを置いたフォルダと、学習の報告（Markdown）を返す。期間は架空の1シーズンに合わせる。"""
    folder = tmp_path_factory.mktemp("trained")
    models, out = folder / "models", folder / "report.md"
    with pytest.raises(SystemExit) as stopped:
        CommandLine().run([
            "train", "--config", str(fast_settings_path), "--warmup-from", season.FIRST_RACE_DAY.isoformat(),
            "--train-from", season.TRAIN_FIRST_DAY.isoformat(), "--valid-from", season.VALID_FIRST_DAY.isoformat(),
            "--test-from", season.TEST_FIRST_DAY.isoformat(), "--figure-cache", str(figure_cache),
            "--db", str(season_db), "--models", str(models), "--out", str(out),
        ])
    assert stopped.value.code == 0
    return models, out.read_text(encoding="utf-8")
