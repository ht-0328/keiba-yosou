"""研究「一番人気を疑う」から移した2つの直し方（木曜の馬の力の材料・当日の券種の支持）の組み立て。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from 共通 import db

from yosou.shared.dataset import HORSE_ID, RACE_DATE, RACE_ID, PredictionData, TrainingData
from yosou.shared.feature import ABILITY_FEATURES, POOL_SUPPORT_NAMES, PredictionTiming
from yosou.shared.tests import synthetic_season as season

from ..dataset import PoolAvailability, PoolFreeData, ability_dataset_builder
from ..feature import ABILITY_CATALOG, CATALOG, POOL_CATALOG, RACE_DAY_CATALOG
from ..workflow import ABILITY_TIMINGS, FORM_TIMINGS

#: M のうち、どの時点でも分かり、合成のシーズンでも値が入る列（例として確かめる）。
_FIGURE = "指数_前走"


def test_the_catalogs_split_by_timing():
    # 木曜・前日は馬の力の材料（木曜は M だけ、前日は J も）。当日は今の材料に N と M を足す
    assert ABILITY_TIMINGS == (PredictionTiming.THURSDAY, PredictionTiming.DAY_BEFORE)
    assert len(ABILITY_CATALOG.columns_for(PredictionTiming.DAY_BEFORE)) == 199 + 7 + 4
    assert set(ABILITY_TIMINGS) | set(FORM_TIMINGS) == set(PredictionTiming)
    assert len(ABILITY_CATALOG.columns_for(PredictionTiming.THURSDAY)) == 192 + 7
    assert len(POOL_CATALOG.columns_for(PredictionTiming.RACE_DAY)) == len(CATALOG.columns_for(PredictionTiming.RACE_DAY)) + 6
    assert POOL_CATALOG.columns_for(PredictionTiming.DAY_BEFORE) == CATALOG.columns_for(PredictionTiming.DAY_BEFORE)
    assert all(feature.group == "M" and not feature.is_categorical for feature in ABILITY_FEATURES)
    # 当日の M は、今の材料と同じ名前の2つ（前走からの日数・芝ダ替わり）を除いた 200個
    assert len(RACE_DAY_CATALOG.columns_for(PredictionTiming.RACE_DAY)) == 79 + 6 + 200


def test_ability_training_data_has_the_ability_features(ability_training_data: TrainingData):
    assert list(ability_training_data.features.columns) == list(ABILITY_CATALOG.names)
    assert ability_training_data.ids[RACE_DATE].min() >= pd.Timestamp(season.TRAIN_FIRST_DAY)
    # 学習データの始まりの日の馬にも、ウォームアップ期間の走から作ったスピード指数の列が入る
    assert ability_training_data.features[_FIGURE].notna().mean() > 0.5
    # どれも小数（カテゴリの列は無い）
    assert all(dtype == np.float64 for dtype in ability_training_data.features.dtypes)


def _prediction(season_db: Path, figure_cache: Path, race_id: str, timing: PredictionTiming) -> PredictionData:
    with db.open_db(season_db) as con:
        return ability_dataset_builder(con, figure_cache).build_prediction_data(race_id, timing)


def test_ability_features_are_the_same_in_training_and_prediction(season_db: Path, figure_cache: Path,
                                                                   ability_training_data: TrainingData):
    # いちばん最後の日の終わったレースを、予測用データとして作り直しても、学習データと同じ値になる（設計書 11 の 4）
    ids = ability_training_data.ids
    race_id = ids.loc[ids[RACE_DATE] == ids[RACE_DATE].max(), RACE_ID].iloc[0]
    data = _prediction(season_db, figure_cache, race_id, PredictionTiming.RACE_DAY)
    columns = [feature.name for feature in ABILITY_FEATURES]
    predicted = data.features[columns].set_axis(data.ids[HORSE_ID].to_numpy())
    rows = ids[RACE_ID] == race_id
    trained = ability_training_data.features.loc[rows, columns].set_axis(ids.loc[rows, HORSE_ID].to_numpy())
    pd.testing.assert_frame_equal(predicted.sort_index(), trained.sort_index(), check_dtype=False)


def test_thursday_ability_prediction_needs_no_horse_numbers(season_db: Path, figure_cache: Path):
    data = _prediction(season_db, figure_cache, season.ENTRY_LIST_RACE_ID, PredictionTiming.THURSDAY)
    assert len(data) == 8 and list(data.features.columns) == list(ABILITY_CATALOG.columns_for(PredictionTiming.THURSDAY))
    assert data.features[_FIGURE].notna().any() and data.baseline is None


def _pool_data(values: list[list[float]]) -> PredictionData:
    """2頭の予測用データ（N の6列と、今の材料の列を1つ）。"""
    features = pd.DataFrame(values, columns=list(POOL_SUPPORT_NAMES)).assign(距離=[1600.0, 1600.0])
    return PredictionData(ids=pd.DataFrame(index=features.index), features=features,
                          timing=PredictionTiming.RACE_DAY, catalog=POOL_CATALOG)


def test_pool_odds_are_missing_when_any_pool_is_missing_for_every_horse():
    nothing = [[np.nan] * 6, [np.nan] * 6]
    one_pool_missing = [[np.nan] + [0.1] * 5, [np.nan] + [0.2] * 5]
    one_horse_missing = [[0.1] * 6, [np.nan] * 6]
    assert PoolAvailability().missing(_pool_data(nothing))
    # 1つの券種が丸ごと無いときも、券種の支持を使わないモデルにする（学習データにはほとんど無い形のため）
    assert PoolAvailability().missing(_pool_data(one_pool_missing))
    # 一部の馬だけ無いときは、券種の支持を使うモデルのまま
    assert not PoolAvailability().missing(_pool_data(one_horse_missing))


def test_pool_free_data_drops_the_pool_columns():
    data = PoolFreeData().prediction(_pool_data([[0.1] * 6, [0.2] * 6]))
    assert list(data.features.columns) == ["距離"] and data.catalog.names == CATALOG.names


@pytest.mark.parametrize("timing", [PredictionTiming.THURSDAY, PredictionTiming.DAY_BEFORE])
def test_pool_odds_are_never_missing_before_race_day(timing: PredictionTiming):
    data = PredictionData(ids=pd.DataFrame(index=[0]), features=pd.DataFrame({"距離": [1600.0]}), timing=timing,
                          catalog=POOL_CATALOG)
    assert not PoolAvailability().missing(data)
