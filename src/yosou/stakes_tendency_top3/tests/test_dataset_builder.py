"""学習データ・予測用データの作り方（設計書 06 の図1・08・10）。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from 共通 import db

from yosou.shared.dataset import RACE_DATE, RACE_ID, TrainingData
from yosou.shared.dataset.column_names import FINISH
from yosou.shared.feature import PredictionTiming
from yosou.shared.tests import synthetic_season as season
from yosou.shared.tests.synthetic_season.season_plan import FIELD_SIZE

from ..dataset import TOP3, WIN, dataset_builder
from ..feature import CATALOG
from ..feature.stakes_tendency_features import EDITIONS, FRONT_GAP, FRONT_GAP_SELF

#: 架空の1シーズンの重賞（テスト記念）のレース番号と、終わった開催の rid の例（2024年12月の最初の土曜）。
STAKES_RACE_NO = "06"
FINISHED_STAKES_RID = "2024120705010106"
#: 重賞ではない平地のレースの rid（同じ日の 1R）。
FLAT_RID = "2024120705010101"


def test_training_data_keeps_only_stakes_runners(training_data: TrainingData):
    assert (training_data.ids[RACE_ID].str[-2:] == STAKES_RACE_NO).all()
    assert training_data.ids[RACE_DATE].min() >= pd.Timestamp(season.TRAIN_FIRST_DAY)
    assert list(training_data.features.columns) == list(CATALOG.names)


def test_targets_follow_the_final_finish(training_data: TrainingData):
    finish = training_data.evaluation[FINISH].astype("float64")
    assert (training_data.targets[TOP3] == finish.between(1, 3).astype(int)).all()
    assert (training_data.targets[WIN] == (finish == 1).astype(int)).all()


def test_tendency_counts_only_past_editions(training_data: TrainingData):
    """K の「過去開催の数」は、そのレースより前の開催だけを数える（リークなし）。

    学習データの最初の重賞（2024年1月）の前には、ウォームアップ期間（2023年10〜12月）の3開催がある。
    開催を重ねるごとに増える。
    """
    editions = training_data.features[EDITIONS]
    days = training_data.ids[RACE_DATE]
    first_day, last_day = days.min(), days.max()
    assert (editions[days == first_day] == 3).all()
    assert (editions[days == last_day] > 3).all()
    by_day = pd.DataFrame({"day": days, "editions": editions}).groupby("day")["editions"].first()
    assert by_day.is_monotonic_increasing


def test_front_gap_interaction_is_zero_for_non_front_styles(training_data: TrainingData):
    """「前に行く馬のずれ×前に行くか」は、推定脚質が差し・追込（または不明）の馬では 0。"""
    style = training_data.features["推定脚質"].astype("string")
    is_front = style.isin(["逃げ", "先行"]).fillna(False).to_numpy()
    interaction = training_data.features[FRONT_GAP_SELF].to_numpy()
    gap = training_data.features[FRONT_GAP].to_numpy()
    assert (interaction[~is_front] == 0).all()
    assert (interaction[is_front] == gap[is_front]).all()


def test_prediction_works_for_a_finished_stakes_race(season_db: Path):
    with db.open_db(season_db) as con:
        data = dataset_builder(con).build_prediction_data(FINISHED_STAKES_RID, PredictionTiming.RACE_DAY)
    assert len(data.ids) == FIELD_SIZE
    assert list(data.features.columns) == list(CATALOG.columns_for(PredictionTiming.RACE_DAY))
    assert (data.features[EDITIONS] > 0).all()


def test_prediction_rejects_non_stakes_races(season_db: Path):
    with db.open_db(season_db) as con:
        with pytest.raises(ValueError, match="重賞"):
            dataset_builder(con).build_prediction_data(FLAT_RID, PredictionTiming.RACE_DAY)
