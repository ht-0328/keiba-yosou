"""共通の部品（``shared``）のテストの準備。予想のパッケージ（``form_aptitude_top3`` など）は使わない。

``DatasetBuilder`` と設定の読み込みは、予想ごとに違うもの（入れる行・目的変数・初期値のファイル）を
受け取る。このテストでは、その代わりにここのいちばん簡単なもの（``AllRunnersSelector``・
``TopFinishLabeler``・``DEFAULT_SETTINGS``）を渡す。

| フィクスチャ | 中身 |
|---|---|
| ``training_data`` | 架空の1シーズンから作った学習データ（出走した全頭・特徴量 71個） |
| ``default_settings_path`` | テスト用の初期値の設定ファイルのパス |

合成DB（``season_db``）と期間（``season_period``）は ``src/yosou/conftest.py``。
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from 共通 import db

from ..dataset import DatasetBuilder, HistoryRecordsLoader, RaceRecordsLoader, TrainingData, TrainingPeriod
from ..feature import BASE_FEATURES, FeatureBuilder, FeatureCatalog

#: どの予想でも使う特徴量 71個の一覧。
CATALOG = FeatureCatalog(BASE_FEATURES)
#: テスト用の目的変数の列の名前。
LABEL_NAME = "目的変数"
#: 3着以内に入った着順のうち、いちばん大きいもの。
_LAST_PLACE = 3

#: テスト用の初期値の設定（予想ごとの ``default_settings.toml`` の代わり。項目の名前と形は同じ）。
DEFAULT_SETTINGS = """
[lightgbm]
early_stopping_rounds = 100
min_category_count = 2000

[lightgbm.params]
learning_rate = 0.05
n_estimators = 2000
num_leaves = 31
min_child_samples = 100
subsample = 0.8
subsample_freq = 1
colsample_bytree = 0.8
random_state = 42

[catboost]
early_stopping_rounds = 100

[catboost.params]
learning_rate = 0.05
iterations = 2000
depth = 6
l2_leaf_reg = 3
random_seed = 42
"""


class AllRunnersSelector:
    """``SampleSelector`` を守る、テスト用のいちばん簡単な行の選び方（出走した行を全部入れる）。"""

    def training_samples(self, entries: pd.DataFrame, train_first_day: date) -> pd.DataFrame:
        runners = self._runners(entries)
        return runners[runners["race_date"] >= pd.Timestamp(train_first_day)]

    def prediction_runners(self, entries: pd.DataFrame, race_id: str) -> pd.DataFrame:
        return self._runners(entries)

    def keep_samples(self, rows: pd.DataFrame) -> pd.DataFrame:
        return rows

    def _runners(self, entries: pd.DataFrame) -> pd.DataFrame:
        return entries[entries["ran"].eq(True)]


class TopFinishLabeler:
    """``TargetLabeler`` を守る、テスト用のいちばん簡単な目的変数（3着以内なら 1）。"""

    @property
    def label_name(self) -> str:
        return LABEL_NAME

    def build(self, samples: pd.DataFrame) -> pd.DataFrame:
        finish = pd.to_numeric(samples["finish"], errors="coerce").astype("float64")
        return pd.DataFrame(
            {LABEL_NAME: finish.between(1, _LAST_PLACE).astype(int)}, index=samples.index,
        )


@pytest.fixture(scope="session")
def training_data(season_db: Path, season_period: TrainingPeriod) -> TrainingData:
    """架空の1シーズンの学習データ。"""
    with db.open_db(season_db) as con:
        builder = DatasetBuilder(
            HistoryRecordsLoader(con), RaceRecordsLoader(con),
            AllRunnersSelector(), TopFinishLabeler(), FeatureBuilder(CATALOG),
        )
        return builder.build_training_data(season_period)


@pytest.fixture(scope="session")
def default_settings_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """テスト用の初期値の設定ファイル。"""
    path = tmp_path_factory.mktemp("defaults") / "default_settings.toml"
    path.write_text(DEFAULT_SETTINGS, encoding="utf-8")
    return path
