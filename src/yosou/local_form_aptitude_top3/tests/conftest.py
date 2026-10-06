"""この予想のテストの準備。実DB は使わず、地方の合成DB（架空の地方の1シーズン。``yosou.shared.tests.local_season``）だけを使う。

速い設定（``fast_settings_path``）は ``src/yosou/conftest.py``。ここには、地方の合成DB と、この予想の組み立てで作るものを置く。

| フィクスチャ | 中身 |
|---|---|
| ``local_season_db`` | 架空の地方の1シーズンの合成DB のパス |
| ``local_season_period`` | そのシーズンに合わせた学習データの期間 |
| ``training_data`` | 学習データ（出走した全頭・3着以内・特徴量 96個） |
| ``trained`` | 本番と同じ学習（train コマンド）を1回通した結果（モデルを置いたフォルダと、学習の報告の文章） |
"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import db
from 合成DB import synth

from yosou.shared.dataset import TrainingData, TrainingPeriod
from yosou.shared.tests import local_season as season

from ..command import CommandLine
from ..dataset import local_dataset_builder


@pytest.fixture(scope="session")
def local_season_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """架空の地方の1シーズンの合成DB のパス。"""
    return synth.build_db(tmp_path_factory.mktemp("local_season") / "local_season.duckdb", season.LocalSeasonBuilder().build())


@pytest.fixture(scope="session")
def local_season_period() -> TrainingPeriod:
    """架空のシーズンに合わせた期間（ウォームアップ 2023-10-07・学習 2024-01-01・検証 2024-07-01・テスト 2024-10-01 から）。"""
    return TrainingPeriod(season.FIRST_RACE_DAY, season.TRAIN_FIRST_DAY, season.VALID_FIRST_DAY, season.TEST_FIRST_DAY)


@pytest.fixture(scope="session")
def training_data(local_season_db: Path, local_season_period: TrainingPeriod) -> TrainingData:
    """架空の地方の1シーズンの学習データ。"""
    with db.open_db(local_season_db) as con:
        return local_dataset_builder(con).build_training_data(local_season_period)


@pytest.fixture(scope="session")
def trained(local_season_db: Path, fast_settings_path: Path, tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str]:
    """train コマンドを1回通して、モデルを置いたフォルダと、学習の報告（Markdown）を返す。"""
    folder = tmp_path_factory.mktemp("trained")
    models, out = folder / "models", folder / "report.md"
    with pytest.raises(SystemExit) as stopped:
        CommandLine().run([
            "train", "--config", str(fast_settings_path), "--warmup-from", season.FIRST_RACE_DAY.isoformat(),
            "--train-from", season.TRAIN_FIRST_DAY.isoformat(), "--valid-from", season.VALID_FIRST_DAY.isoformat(),
            "--test-from", season.TEST_FIRST_DAY.isoformat(),
            "--db", str(local_season_db), "--models", str(models), "--out", str(out),
        ])
    assert stopped.value.code == 0
    return models, out.read_text(encoding="utf-8")
