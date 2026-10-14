"""学習データ・予測用データの作り方（設計書 06 の図1・08・10）。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from 共通 import db

from yosou.form_aptitude_top3.feature import ABILITY_CATALOG as FORM_ABILITY_CATALOG
from yosou.form_aptitude_top3.feature import RACE_DAY_CATALOG as FORM_RACE_DAY_CATALOG
from yosou.shared.dataset import RACE_DATE, RACE_ID, TrainingData
from yosou.shared.dataset.column_names import FINISH
from yosou.shared.feature import PredictionTiming
from yosou.shared.tests import synthetic_season as season
from yosou.shared.tests.synthetic_season.season_plan import FIELD_SIZE

from ..dataset import TOP3, WIN, ability_dataset_builder, race_day_dataset_builder
from ..feature import ABILITY_CATALOG, K_FEATURES, RACE_DAY_CATALOG
from ..feature.tendency_cut import EDITIONS, RUNS, STATS, cut_keyed
from ..workflow import ABILITY_TIMINGS, FORM_TIMINGS

#: 架空の1シーズンの重賞（テスト記念）のレース番号と、終わった開催の rid の例（2024年12月の最初の土曜）。
STAKES_RACE_NO = "06"
FINISHED_STAKES_RID = "2024120705010106"
#: 重賞ではない平地のレースの rid（同じ日の 1R）。
FLAT_RID = "2024120705010101"


def test_the_catalogs_are_the_form_catalogs_plus_the_tendency():
    """材料は手本と同じ構成に K を足したもの（設計書 15 の 10）。木曜は枠・オッズ・人気の切り口（12個）を除く K の39個。"""
    k_names = tuple(feature.name for feature in K_FEATURES)
    assert len(k_names) == 51 and len(set(k_names)) == 51
    assert ABILITY_CATALOG.names == FORM_ABILITY_CATALOG.names + k_names
    assert RACE_DAY_CATALOG.names == FORM_RACE_DAY_CATALOG.names + k_names
    assert len(ABILITY_CATALOG.columns_for(PredictionTiming.THURSDAY)) == 199 + 39
    assert len(ABILITY_CATALOG.columns_for(PredictionTiming.DAY_BEFORE)) == 210 + 51
    assert len(RACE_DAY_CATALOG.columns_for(PredictionTiming.RACE_DAY)) == 285 + 51
    assert ABILITY_TIMINGS == (PredictionTiming.THURSDAY, PredictionTiming.DAY_BEFORE) and FORM_TIMINGS == (PredictionTiming.RACE_DAY,)


def test_training_data_keeps_only_stakes_runners(race_day_training_data: TrainingData, ability_training_data: TrainingData):
    for data, catalog in ((race_day_training_data, RACE_DAY_CATALOG), (ability_training_data, ABILITY_CATALOG)):
        assert (data.ids[RACE_ID].str[-2:] == STAKES_RACE_NO).all()
        assert data.ids[RACE_DATE].min() >= pd.Timestamp(season.TRAIN_FIRST_DAY)
        assert list(data.features.columns) == list(catalog.names)
    # 木曜・前日の材料はどれも小数（カテゴリの列は無い）。学習データの始まりの馬にもスピード指数が入る
    assert all(dtype == np.float64 for dtype in ability_training_data.features.dtypes)
    assert ability_training_data.features["指数_前走"].notna().mean() > 0.5


def test_targets_follow_the_final_finish(race_day_training_data: TrainingData):
    finish = race_day_training_data.evaluation[FINISH].astype("float64")
    assert (race_day_training_data.targets[TOP3] == finish.between(1, 3).astype(int)).all()
    assert (race_day_training_data.targets[WIN] == (finish == 1).astype(int)).all()


def test_tendency_counts_only_past_editions(race_day_training_data: TrainingData, ability_training_data: TrainingData):
    """K の「過去開催の数」は、そのレースより前の開催だけを数える（リークなし）。

    学習データの最初の重賞（2024年1月）の前には、ウォームアップ期間（2023年10〜12月）の3開催がある。
    開催を重ねるごとに増える。どちらの材料でも同じ値になる。
    """
    for data in (race_day_training_data, ability_training_data):
        editions = data.features[EDITIONS]
        days = data.ids[RACE_DATE]
        assert (editions[days == days.min()] == 3).all() and (editions[days == days.max()] > 3).all()
        by_day = pd.DataFrame({"day": days, "editions": editions}).groupby("day")["editions"].first()
        assert by_day.is_monotonic_increasing


def test_the_style_cut_counts_the_runners_of_the_horse_s_own_style_band(race_day_training_data: TrainingData):
    """「脚質が同じ馬」は、推定脚質が前（逃げ・先行）の馬には過去の前の馬を、後ろの馬には後ろの馬を数える。

    同じレースの前の馬どうし（後ろの馬どうし）は同じ値になり、前と後ろで値が違うレースがある。
    """
    style = race_day_training_data.features["推定脚質"].astype("string")
    runs = race_day_training_data.features[cut_keyed("style").feature_name(RUNS)]
    frame = pd.DataFrame({"race": race_day_training_data.ids[RACE_ID], "front": style.isin(["逃げ", "先行"]).fillna(False).to_numpy(),
                          "runs": runs.to_numpy()})
    with_past = frame[frame["runs"].notna()]
    assert len(with_past) > 0
    assert (with_past.groupby(["race", "front"])["runs"].nunique() == 1).all()
    # 切り口ごとの4つの成績は、出走数が無い（欠損）ならほかの3つも欠損
    for key in ("prev_race", "frame", "odds", "popularity", "age"):
        columns = [cut_keyed(key).feature_name(stat) for stat in STATS]
        table = race_day_training_data.features[columns]
        assert (table.isna().all(axis=1) | table.notna().all(axis=1)).all()


def test_prediction_works_for_a_finished_stakes_race(season_db: Path, figure_cache: Path):
    with db.open_db(season_db) as con:
        race_day = race_day_dataset_builder(con, figure_cache).build_prediction_data(FINISHED_STAKES_RID, PredictionTiming.RACE_DAY)
        thursday = ability_dataset_builder(con, figure_cache).build_prediction_data(FINISHED_STAKES_RID, PredictionTiming.THURSDAY)
    assert len(race_day.ids) == FIELD_SIZE and len(thursday.ids) == FIELD_SIZE
    assert list(race_day.features.columns) == list(RACE_DAY_CATALOG.columns_for(PredictionTiming.RACE_DAY))
    assert list(thursday.features.columns) == list(ABILITY_CATALOG.columns_for(PredictionTiming.THURSDAY))
    assert (race_day.features[EDITIONS] > 0).all() and (thursday.features[EDITIONS] > 0).all()
    # 木曜はオッズから作った基準を使わない
    assert thursday.baseline is None and race_day.baseline is not None


def test_prediction_rejects_non_stakes_races(season_db: Path, figure_cache: Path):
    with db.open_db(season_db) as con:
        with pytest.raises(ValueError, match="重賞"):
            race_day_dataset_builder(con, figure_cache).build_prediction_data(FLAT_RID, PredictionTiming.RACE_DAY)
