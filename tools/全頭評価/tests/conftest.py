"""全頭評価のテストの準備。実DB は使わず、架空の1シーズンの合成DB（特別登録つき）で予想を学習して使う。

| フィクスチャ | 中身 |
|---|---|
| ``season_db`` | 架空の1シーズンの合成DB のパス（``yosou.shared.tests.synthetic_season``） |
| ``figure_cache`` | スピード指数をとっておく一時フォルダ |
| ``review_models`` | 速い設定で学習した予想のモデルの置き場所 |
"""

from __future__ import annotations

from pathlib import Path

import pytest

from 合成DB import synth

from yosou.shared.tests import synthetic_season as season
from yosou.special_registration_top3.command import CommandLine

#: テストで速く学習が終わる設定。
_FAST_SETTINGS = """
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
def season_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return synth.build_db(tmp_path_factory.mktemp("season") / "season.duckdb", season.SeasonBuilder().build())


@pytest.fixture(scope="session")
def figure_cache(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("figures")


@pytest.fixture(scope="session")
def review_models(season_db: Path, figure_cache: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """train コマンドを1回通して、モデルを置いたフォルダを返す。"""
    folder = tmp_path_factory.mktemp("review")
    settings = folder / "fast.toml"
    settings.write_text(_FAST_SETTINGS, encoding="utf-8")
    models = folder / "models"
    with pytest.raises(SystemExit) as stopped:
        CommandLine().run([
            "train", "--config", str(settings), "--warmup-from", season.FIRST_RACE_DAY.isoformat(),
            "--train-from", season.TRAIN_FIRST_DAY.isoformat(), "--valid-from", season.VALID_FIRST_DAY.isoformat(),
            "--test-from", season.TEST_FIRST_DAY.isoformat(), "--figure-cache", str(figure_cache),
            "--db", str(season_db), "--models", str(models), "--out", str(folder / "train.md"),
        ])
    assert stopped.value.code == 0
    return models
