"""テストの共通の準備。実DB は使わず、合成DB（架空の1シーズン。``synthetic_season/``）だけを使う。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import db
from 合成DB import synth

from ..dataset import DatasetBuilder, TrainingData, TrainingPeriod
from ..ml_model import MEMBER_TYPES
from ..repository import ModelRepository
from ..workflow import TrainingReport, TrainingWorkflow
from . import synthetic_season as season

#: テストで速く学習が終わる設定（木の数を少なく、葉のサンプル数とカテゴリの出走数の下限を小さく）。
FAST_SETTINGS = """
[lightgbm]
early_stopping_rounds = 10
min_category_count = 20

[lightgbm.params]
n_estimators = 60
min_child_samples = 20

[catboost]
early_stopping_rounds = 10

[catboost.params]
iterations = 60
depth = 4
"""


@pytest.fixture(scope="session")
def season_sample() -> synth.Sample:
    """架空の1シーズンの行の束。"""
    return season.SeasonBuilder().build()


@pytest.fixture(scope="session")
def season_db(season_sample: synth.Sample, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """架空の1シーズンの合成DB のパス。"""
    return synth.build_db(tmp_path_factory.mktemp("season") / "season.duckdb", season_sample)


@pytest.fixture(scope="session")
def fast_settings_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("settings") / "fast.toml"
    path.write_text(FAST_SETTINGS, encoding="utf-8")
    return path


@pytest.fixture(scope="session")
def season_period() -> TrainingPeriod:
    """架空の1シーズンに合わせた期間（ウォームアップ 2023-10-07・学習 2024-01-01・検証 2024-07-01・テスト 2024-10-01 から）。"""
    return TrainingPeriod(
        season.FIRST_RACE_DAY, season.TRAIN_FIRST_DAY, season.VALID_FIRST_DAY, season.TEST_FIRST_DAY,
    )


@pytest.fixture(scope="session")
def training_data(season_db: Path, season_period: TrainingPeriod) -> TrainingData:
    """架空の1シーズンの学習データ。"""
    with db.open_db(season_db) as con:
        return DatasetBuilder.for_database(con).build_training_data(season_period)


@pytest.fixture(scope="session")
def trained(season_db: Path, fast_settings_path: Path, season_period: TrainingPeriod,
            tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, TrainingReport]:
    """学習の流れを1回通して、モデルを置いたフォルダと学習の結果を返す。"""
    models = tmp_path_factory.mktemp("models")
    with db.open_db(season_db) as con:
        workflow = TrainingWorkflow(
            DatasetBuilder.for_database(con), season_period, ModelRepository(models, MEMBER_TYPES),
        )
        report = workflow.run(fast_settings_path)
    return models, report
