"""この予想のテストの準備。実DB は使わず、合成DB（架空の1シーズン）だけを使う。

合成DB（``season_db``）・速い設定（``fast_settings_path``）・期間（``season_period``）は
``src/yosou/conftest.py``。ここには、この予想の組み立てで作るものを置く。

| フィクスチャ | 中身 |
|---|---|
| ``training_data`` | 今の材料の学習データ（出走した全頭・3着以内・特徴量 79個） |
| ``figure_cache`` | スピード指数をとっておく一時フォルダ（本物の ``reports/能力指数/cache/`` を書き換えない） |
| ``ability_training_data`` | 馬の力の材料の学習データ（M の 202個と J の4個） |
| ``trained`` | 本番と同じ学習（train コマンド）を1回通した結果（モデルを置いたフォルダと、学習の報告の文章） |
"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import db

from yosou.shared.dataset import TrainingData, TrainingPeriod
from yosou.shared.tests import synthetic_season as season

from ..command import CommandLine
from ..dataset import ability_dataset_builder, dataset_builder


@pytest.fixture(scope="session")
def training_data(season_db: Path, season_period: TrainingPeriod) -> TrainingData:
    """架空の1シーズンの学習データ（今の材料）。"""
    with db.open_db(season_db) as con:
        return dataset_builder(con).build_training_data(season_period)


@pytest.fixture(scope="session")
def figure_cache(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """スピード指数をとっておく一時フォルダ。"""
    return tmp_path_factory.mktemp("figures")


@pytest.fixture(scope="session")
def ability_training_data(season_db: Path, season_period: TrainingPeriod, figure_cache: Path) -> TrainingData:
    """架空の1シーズンの学習データ（馬の力の材料）。"""
    with db.open_db(season_db) as con:
        return ability_dataset_builder(con, figure_cache).build_training_data(season_period)


@pytest.fixture(scope="session")
def trained(season_db: Path, fast_settings_path: Path, figure_cache: Path,
            tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str]:
    """train コマンドを1回通して、モデルを置いたフォルダと、学習の報告（Markdown）を返す。

    期間は架空の1シーズンに合わせる（馬の力の材料も、今の材料と同じ 2024-01-01 から学ぶ）。
    """
    folder = tmp_path_factory.mktemp("trained")
    models, out = folder / "models", folder / "report.md"
    with pytest.raises(SystemExit) as stopped:
        CommandLine().run([
            "train", "--config", str(fast_settings_path), "--warmup-from", season.FIRST_RACE_DAY.isoformat(),
            "--train-from", season.TRAIN_FIRST_DAY.isoformat(), "--ability-train-from", season.TRAIN_FIRST_DAY.isoformat(),
            "--valid-from", season.VALID_FIRST_DAY.isoformat(), "--test-from", season.TEST_FIRST_DAY.isoformat(),
            "--figure-cache", str(figure_cache), "--db", str(season_db), "--models", str(models), "--out", str(out),
        ])
    assert stopped.value.code == 0
    return models, out.read_text(encoding="utf-8")
