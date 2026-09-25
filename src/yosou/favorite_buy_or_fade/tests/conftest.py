"""この予想のテストの準備。実DB は使わず、合成DB（架空の1シーズン）だけを使う。

合成DB（``season_db``）は ``src/yosou/conftest.py``。ここには、この予想の組み立てで作るものを置く。

| フィクスチャ | 中身 |
|---|---|
| ``small_settings_path`` | 架空の1シーズンに合わせた方針のファイル（2023年から学習し、2024年を評価する） |
| ``small_settings`` | そのファイルを読んだ方針 |
| ``training_data`` | この予想の学習データ（1番人気の行・3つのグループの列・特徴量 A〜K） |
"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import db

from yosou.shared.dataset import TrainingData

from ..setting import BuyOrFadeSettings
from ..workflow import TrainingDataReader

#: 架空のシーズン（2023年10月〜2024年12月）に合わせた方針。頭数が少ないので、単位の下限と k を小さくする。
SMALL_SETTINGS = """
[unit]
min_rows = 20

[similarity]
k = 3

[evaluation]
train_first_year = 2023
first_year = 2024
last_year = 2024
"""


@pytest.fixture(scope="session")
def small_settings_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("buy-or-fade-settings") / "small.toml"
    path.write_text(SMALL_SETTINGS, encoding="utf-8")
    return path


@pytest.fixture(scope="session")
def small_settings(small_settings_path: Path) -> BuyOrFadeSettings:
    return BuyOrFadeSettings.load(small_settings_path)


@pytest.fixture(scope="session")
def training_data(season_db: Path, small_settings: BuyOrFadeSettings) -> TrainingData:
    """架空の1シーズンの学習データ（1番人気の行だけ）。"""
    with db.open_db(season_db) as con:
        return TrainingDataReader(small_settings).read(con)
