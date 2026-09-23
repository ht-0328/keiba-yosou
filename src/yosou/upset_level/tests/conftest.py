"""この予想のテストの準備。実DB は使わず、合成DB（架空の1シーズン）だけを使う。

合成DB（``season_db``）・速い設定（``fast_settings_path``）・期間（``season_period``）は
``src/yosou/conftest.py``。ここには、この予想の組み立てで作るものを置く。

| フィクスチャ | 中身 |
|---|---|
| ``training_data`` | この予想の学習データ（1行 = 1レース。目的変数は券種ごとの4列、特徴量 49個） |
| ``trained`` | 2つの券種（単勝・3連単）について学習の流れを通した結果（モデルを置いたフォルダと、券種ごとの ``TrainingReport``） |
"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import db

from yosou.shared.dataset import TrainingData, TrainingPeriod
from yosou.shared.evaluation import ClassModelEvaluator, TrainingReport
from yosou.shared.ml_model import CLASS_MEMBER_TYPES
from yosou.shared.workflow import TrainingWorkflow

from ..dataset import BetType, race_dataset_builder
from ..setting import DEFAULT_SETTINGS_PATH
from ..workflow import TIMINGS, model_repositories

#: テストで学習する券種（4つ全部だと時間がかかるので、両端の2つ）。
TRAINED_BETS: tuple[BetType, ...] = (BetType.WIN, BetType.TRIFECTA)


@pytest.fixture(scope="session")
def training_data(season_db: Path, season_period: TrainingPeriod) -> TrainingData:
    """架空の1シーズンの学習データ（1行 = 1レース）。"""
    with db.open_db(season_db) as con:
        return race_dataset_builder(con).build_training_data(season_period)


@pytest.fixture(scope="session")
def trained(training_data: TrainingData, season_db: Path, fast_settings_path: Path,
            season_period: TrainingPeriod,
            tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict[BetType, TrainingReport]]:
    """2つの券種について学習の流れを通して、モデルを置いたフォルダと、券種ごとの学習の結果を返す。"""
    models = tmp_path_factory.mktemp("models")
    repositories = model_repositories(models)
    reports: dict[BetType, TrainingReport] = {}
    with db.open_db(season_db) as con:
        builder = race_dataset_builder(con)
    for bet in TRAINED_BETS:
        workflow = TrainingWorkflow(
            builder, season_period, repositories[bet], TIMINGS, DEFAULT_SETTINGS_PATH,
            member_types=CLASS_MEMBER_TYPES, evaluator=ClassModelEvaluator(),
        )
        reports[bet] = workflow.train(training_data.with_label(bet.column_name), fast_settings_path)
    return models, reports
