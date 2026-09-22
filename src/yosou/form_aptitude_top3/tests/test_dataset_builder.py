"""学習データ・予測用データの作り方（設計書 06 の図1・08・10）。"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from 共通 import db
from 合成DB import synth

from ..dataset import HORSE_NO, RACE_DATE, RACE_ID, TOP3, WIN, DatasetBuilder, PredictionData, TrainingData
from ..dataset.column_names import FINISH
from ..feature import FEATURE_NAMES, PredictionTiming
from . import synthetic_season as season


def _prediction(path: Path, race_id: str, timing: PredictionTiming) -> PredictionData:
    with db.open_db(path) as con:
        return DatasetBuilder.for_database(con).build_prediction_data(race_id, timing)


def test_training_data_keeps_flat_runners_from_the_train_first_day(training_data: TrainingData):
    assert training_data.ids[RACE_DATE].min() >= pd.Timestamp(season.TRAIN_FIRST_DAY)
    assert set(training_data.features["芝ダ"]) == {"芝", "ダート"}
    assert list(training_data.features.columns) == list(FEATURE_NAMES)
    assert training_data.features.index.equals(training_data.ids.index)


def test_targets_follow_the_final_finish(training_data: TrainingData):
    finish = training_data.evaluation[FINISH].astype("float64")
    assert (training_data.targets[TOP3] == finish.between(1, 3).astype(int)).all()
    assert (training_data.targets[WIN] == (finish == 1).astype(int)).all()
    # 競走中止（着順なし）の馬は、走ったが3着以内ではないので 0
    is_stopped = finish.isna()
    assert is_stopped.any() and (training_data.targets.loc[is_stopped, TOP3] == 0).all()


def test_warmup_runs_feed_the_first_samples(training_data: TrainingData):
    is_first_day = training_data.ids[RACE_DATE] == training_data.ids[RACE_DATE].min()
    assert (training_data.features.loc[is_first_day, "近5走の数"] > 0).all()


def test_career_counts_are_attached_to_every_sample(training_data: TrainingData):
    assert training_data.features["通算の出走数"].notna().all()


@pytest.mark.parametrize(("timing", "columns"), [
    (PredictionTiming.RACE_DAY, 71), (PredictionTiming.DAY_BEFORE, 69),
])
def test_prediction_data_of_a_card(season_db: Path, timing: PredictionTiming, columns: int):
    data = _prediction(season_db, season.CARD_RACE_ID, timing)
    # 速報で出走取消になった馬番8 は入らない。馬場状態は、最後に発表された「重」
    assert len(data) == 7 and season.SCRATCHED_HORSE_NO not in set(data.ids[HORSE_NO])
    assert data.features.shape[1] == columns and data.timing is timing
    assert set(data.features["馬場状態"]) == {"重"}


def test_race_day_prediction_uses_announced_weights(season_db: Path):
    data = _prediction(season_db, season.CARD_RACE_ID, PredictionTiming.RACE_DAY)
    weights = data.features.set_index(data.ids[HORSE_NO])
    assert (weights.loc[3, "馬体重"], weights.loc[3, "馬体重の増減"]) == (473, -3)


def test_thursday_prediction_works_before_horse_numbers(season_db: Path):
    data = _prediction(season_db, season.ENTRY_LIST_RACE_ID, PredictionTiming.THURSDAY)
    assert len(data) == 8 and data.ids[HORSE_NO].isna().all()
    assert "馬番" not in data.features.columns


def test_day_before_prediction_needs_horse_numbers(season_db: Path):
    with pytest.raises(ValueError, match="馬番"):
        _prediction(season_db, season.ENTRY_LIST_RACE_ID, PredictionTiming.DAY_BEFORE)


def test_race_day_prediction_needs_announced_weights(season_sample: synth.Sample, tmp_path: Path):
    without_weights = replace(season_sample, weight=[], weights=[])
    path = synth.build_db(tmp_path / "no-weights.duckdb", without_weights)
    with pytest.raises(ValueError, match="馬体重"):
        _prediction(path, season.CARD_RACE_ID, PredictionTiming.RACE_DAY)


def test_jump_races_are_not_predicted(season_db: Path):
    with pytest.raises(ValueError, match="障害"):
        _prediction(season_db, season.JUMP_CARD_RACE_ID, PredictionTiming.RACE_DAY)


def test_prediction_of_a_finished_race_matches_training_features(
        season_db: Path, training_data: TrainingData):
    # 学習データと予測用データを同じ作り方で作るので、終わったレースを予測用に作り直しても特徴量は同じになる
    race_id = training_data.ids[RACE_ID].iloc[-1]
    data = _prediction(season_db, race_id, PredictionTiming.RACE_DAY)
    is_same_race = training_data.ids[RACE_ID] == race_id
    expected = training_data.features[is_same_race].reset_index(drop=True)
    pd.testing.assert_frame_equal(data.features.reset_index(drop=True), expected)
