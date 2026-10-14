"""学習データ・予測用データの作り方（設計書 06 の図1・08・09）。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from 共通 import db

from yosou.shared.dataset import HORSE_ID, HORSE_NO, RACE_DATE, RACE_ID, TrainingData
from yosou.shared.feature import PredictionTiming
from yosou.shared.tests import synthetic_season as season
from yosou.shared.tests.synthetic_season.season_plan import STAKES_RACE

from ..dataset import TOP3, WIN, registration_dataset_builder
from ..feature import BASE_CATALOG, SPECIAL_RACE


def test_training_data_has_the_176_builder_features_and_marks_special_races(training_data: TrainingData):
    assert list(training_data.features.columns) == list(BASE_CATALOG.names)
    assert training_data.ids[RACE_DATE].min() >= pd.Timestamp(season.TRAIN_FIRST_DAY)
    assert training_data.baseline is None
    # 特別競走の印: 重賞（テスト記念。レース番号 06）の行だけ 1、平場は 0
    is_stakes = training_data.ids[RACE_ID].astype(str).str.endswith(STAKES_RACE.race_no)
    assert (training_data.features.loc[is_stakes, SPECIAL_RACE] == 1).all()
    assert (training_data.features.loc[~is_stakes, SPECIAL_RACE] == 0).all()
    assert set(training_data.targets.columns) >= {TOP3, WIN}


def test_training_features_are_all_numbers_without_jockey_or_field_size(training_data: TrainingData):
    assert all(pd.api.types.is_float_dtype(dtype) for dtype in training_data.features.dtypes)
    for name in ("騎手_勝率", "field_size", "frame_no", "body_weight", "ブリンカーあり"):
        assert name not in training_data.features.columns
    # 通算の成績（登録日相当まで）は、シーズンの後半の行で値が入る
    late = training_data.ids[RACE_DATE] >= pd.Timestamp(season.VALID_FIRST_DAY)
    assert training_data.features.loc[late, "調教師_出走数"].gt(0).any()


def test_prediction_data_of_a_registration_only_race(season_db: Path, figure_cache: Path):
    with db.open_db(season_db) as con:
        builder = registration_dataset_builder(con, figure_cache)
        data = builder.build_prediction_data(season.REGISTRATION_ONLY_RACE_ID, PredictionTiming.THURSDAY)
        # 人気・オッズを渡しても使わない（RaceRecordsLoader と同じ形）
        same = builder.build_prediction_data(season.REGISTRATION_ONLY_RACE_ID, PredictionTiming.THURSDAY, popularity={"x": 1}, odds={1: 2.0})
    assert len(data) == season.REGISTRATION_ONLY_FIELD_SIZE and list(data.features.columns) == list(BASE_CATALOG.names)
    assert data.ids[HORSE_NO].isna().all() and data.ids[HORSE_ID].notna().all()
    assert (data.features[SPECIAL_RACE] == 1).all() and data.baseline is None
    assert data.features.equals(same.features)


def test_prediction_data_of_the_entry_list_race_comes_from_the_registration(season_db: Path, figure_cache: Path):
    with db.open_db(season_db) as con:
        data = registration_dataset_builder(con, figure_cache).build_prediction_data(season.ENTRY_LIST_RACE_ID, PredictionTiming.THURSDAY)
    # 出走馬名表の8頭ではなく、登録の9頭（地方馬1頭を含む）
    assert len(data) == season.FUTURE_FIELD_SIZE + 1
