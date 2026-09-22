"""予想方法（``src/yosou/``）のテストに共通の準備。

実DB は使わず、合成DB（架空の1シーズン。``yosou.shared.tests.synthetic_season``）だけを使う
（keiba-yosou の決まり）。ここのフィクスチャは、``shared`` のテストからも、予想ごとのテストからも使う。

| フィクスチャ | 中身 |
|---|---|
| ``season_sample`` | 架空の1シーズンの行の束 |
| ``season_db`` | その行を入れた合成DB のパス |
| ``fast_settings_path`` | テストで速く学習が終わる設定ファイルのパス |
| ``season_period`` | 架空の1シーズンに合わせた学習データの期間 |
"""

from __future__ import annotations

from pathlib import Path

import pytest

from 合成DB import synth

from yosou.shared.dataset import TrainingPeriod
from yosou.shared.tests import synthetic_season as season

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
