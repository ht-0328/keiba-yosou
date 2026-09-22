"""この予想のテストの準備。実DB は使わず、合成DB（架空の1シーズン）だけを使う。

合成DB（``season_db``）・速い設定（``fast_settings_path``）・期間（``season_period``）は
``src/yosou/conftest.py``。ここには、この予想の組み立てで作るものを置く。

| フィクスチャ | 中身 |
|---|---|
| ``training_data`` | この予想の学習データ（穴馬の行・3着以内・特徴量 A〜I と J・穴馬の区分） |
| ``trained`` | 学習の流れを1回通した結果（モデルを置いたフォルダと ``TrainingReport``） |
"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import db

from yosou.shared.dataset import TrainingData, TrainingPeriod
from yosou.shared.evaluation import TrainingReport
from yosou.shared.ml_model import MEMBER_TYPES
from yosou.shared.repository import ModelRepository
from yosou.shared.workflow import TrainingWorkflow

from ..dataset import dataset_builder
from ..setting import DEFAULT_SETTINGS_PATH
from ..workflow import TIMINGS


@pytest.fixture(scope="session")
def training_data(season_db: Path, season_period: TrainingPeriod) -> TrainingData:
    """架空の1シーズンの学習データ（穴馬の行だけ）。"""
    with db.open_db(season_db) as con:
        return dataset_builder(con).build_training_data(season_period)


@pytest.fixture(scope="session")
def trained(season_db: Path, fast_settings_path: Path, season_period: TrainingPeriod,
            tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, TrainingReport]:
    """学習の流れを1回通して、モデルを置いたフォルダと学習の結果を返す。"""
    models = tmp_path_factory.mktemp("longshot-models")
    with db.open_db(season_db) as con:
        workflow = TrainingWorkflow(
            dataset_builder(con), season_period, ModelRepository(models, MEMBER_TYPES),
            TIMINGS, DEFAULT_SETTINGS_PATH,
        )
        report = workflow.run(fast_settings_path)
    return models, report
