"""この予想のテストの準備。実DB は使わず、合成DB（架空の1シーズン）だけを使う。

合成DB（``season_db``）・速い設定（``fast_settings_path``）・期間（``season_period``）は
``src/yosou/conftest.py``。ここには、この予想の組み立てで作るものを置く。

| フィクスチャ | 中身 |
|---|---|
| ``training_data`` | この予想の学習データ（人気馬の行・4着以下・特徴量 A〜I と J） |
| ``trained`` | 学習の流れを1回通した結果（モデルを置いたフォルダと ``TrainingReport``） |
"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import db

from yosou.shared.dataset import TrainingData, TrainingPeriod
from yosou.shared.evaluation import TrainingReport
from yosou.shared.workflow import SegmentedTraining

from ..dataset import dataset_builder
from ..setting import DEFAULT_SETTINGS_PATH
from ..workflow import SEGMENTS, TIMINGS


@pytest.fixture(scope="session")
def training_data(season_db: Path, season_period: TrainingPeriod) -> TrainingData:
    """架空の1シーズンの学習データ（人気馬の行だけ）。"""
    with db.open_db(season_db) as con:
        return dataset_builder(con).build_training_data(season_period)


@pytest.fixture(scope="session")
def trained(season_db: Path, fast_settings_path: Path, season_period: TrainingPeriod,
            tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, list[tuple[str, TrainingReport]]]:
    """人気帯ごとの学習を1回通して、モデルを置いたフォルダと（人気帯, 学習の結果）の並びを返す。"""
    models = tmp_path_factory.mktemp("favorite-models")
    with db.open_db(season_db) as con:
        training = SegmentedTraining(SEGMENTS, dataset_builder(con), season_period, models, TIMINGS,
                                     DEFAULT_SETTINGS_PATH)
        training_data = training.read_training_data()
    return models, training.train(training_data, fast_settings_path)
