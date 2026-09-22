"""学習データ・予測用データの作り方（設計書 06 の図1・08・10）。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from 共通 import db
from 合成DB import synth

from yosou.shared.dataset import HORSE_NO, RACE_DATE, RACE_ID, PredictionData, TrainingData
from yosou.shared.dataset.column_names import FINISH
from yosou.shared.feature import PredictionTiming
from yosou.shared.tests import synthetic_season as season

from ..dataset import TOP3, WIN, dataset_builder
from ..feature import CATALOG

#: 出馬表のレース（確定前なので DB にオッズが無い）に、手で渡す単勝オッズ。馬番が小さいほど人気。
CARD_ODDS: dict[int, float] = {horse_no: 1.5 + horse_no for horse_no in range(1, 9)}


def _prediction(path: Path, race_id: str, timing: PredictionTiming,
                odds: Mapping[int, float] | None = None) -> PredictionData:
    with db.open_db(path) as con:
        return dataset_builder(con).build_prediction_data(race_id, timing, odds=odds)


def test_training_data_keeps_flat_runners_from_the_train_first_day(training_data: TrainingData):
    assert training_data.ids[RACE_DATE].min() >= pd.Timestamp(season.TRAIN_FIRST_DAY)
    assert set(training_data.features["芝ダ"]) == {"芝", "ダート"}
    assert list(training_data.features.columns) == list(CATALOG.names)
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


def test_training_market_features_come_from_the_final_odds(training_data: TrainingData):
    # 学習データの単勝オッズは確定オッズ。人気順位はレースごとに 1 から、オッズから見た勝率はレースごとに合計 1
    race_ids = training_data.ids[RACE_ID]
    features = training_data.features
    assert features["単勝オッズ"].notna().all()
    assert (features.groupby(race_ids)["人気順位"].min() == 1).all()
    assert features.groupby(race_ids)["オッズから見た勝率"].sum().round(6).eq(1).all()


@pytest.mark.parametrize(("timing", "columns"), [
    (PredictionTiming.RACE_DAY, 74), (PredictionTiming.DAY_BEFORE, 72),
])
def test_prediction_data_of_a_card(season_db: Path, timing: PredictionTiming, columns: int):
    data = _prediction(season_db, season.CARD_RACE_ID, timing, CARD_ODDS)
    # 速報で出走取消になった馬番8 は入らない。馬場状態は、最後に発表された「重」
    assert len(data) == 7 and season.SCRATCHED_HORSE_NO not in set(data.ids[HORSE_NO])
    assert data.features.shape[1] == columns and data.timing is timing
    assert set(data.features["馬場状態"]) == {"重"}


def test_prediction_market_features_follow_the_given_odds(season_db: Path):
    data = _prediction(season_db, season.CARD_RACE_ID, PredictionTiming.RACE_DAY, CARD_ODDS)
    features = data.features.set_index(data.ids[HORSE_NO])
    assert features.loc[1, "単勝オッズ"] == CARD_ODDS[1] and features.loc[1, "人気順位"] == 1
    assert features["人気順位"].sort_values().tolist() == list(range(1, 8))
    assert round(features["オッズから見た勝率"].sum(), 6) == 1


def test_race_day_prediction_uses_announced_weights(season_db: Path):
    data = _prediction(season_db, season.CARD_RACE_ID, PredictionTiming.RACE_DAY, CARD_ODDS)
    weights = data.features.set_index(data.ids[HORSE_NO])
    assert (weights.loc[3, "馬体重"], weights.loc[3, "馬体重の増減"]) == (473, -3)


def test_thursday_prediction_works_before_horse_numbers_and_odds(season_db: Path):
    data = _prediction(season_db, season.ENTRY_LIST_RACE_ID, PredictionTiming.THURSDAY)
    assert len(data) == 8 and data.ids[HORSE_NO].isna().all()
    assert "馬番" not in data.features.columns and "単勝オッズ" not in data.features.columns


def test_day_before_prediction_needs_horse_numbers(season_db: Path):
    with pytest.raises(ValueError, match="馬番"):
        _prediction(season_db, season.ENTRY_LIST_RACE_ID, PredictionTiming.DAY_BEFORE)


def test_day_before_prediction_needs_odds(season_db: Path):
    # 確定前のレースは DB にオッズが無く、合成DB には締め切り前のオッズの表も無い
    with pytest.raises(ValueError, match="--odds"):
        _prediction(season_db, season.CARD_RACE_ID, PredictionTiming.DAY_BEFORE)


def test_race_day_prediction_needs_announced_weights(season_sample: synth.Sample, tmp_path: Path):
    without_weights = replace(season_sample, weight=[], weights=[])
    path = synth.build_db(tmp_path / "no-weights.duckdb", without_weights)
    with pytest.raises(ValueError, match="馬体重"):
        _prediction(path, season.CARD_RACE_ID, PredictionTiming.RACE_DAY, CARD_ODDS)


def test_jump_races_are_not_predicted(season_db: Path):
    with pytest.raises(ValueError, match="障害"):
        _prediction(season_db, season.JUMP_CARD_RACE_ID, PredictionTiming.RACE_DAY)


def test_prediction_of_a_finished_race_matches_training_features(
        season_db: Path, training_data: TrainingData):
    # 学習データと予測用データを同じ作り方で作るので、終わったレースを予測用に作り直しても特徴量は同じになる
    # （オッズを渡さなければ、DB の確定オッズがそのまま使われる）
    race_id = training_data.ids[RACE_ID].iloc[-1]
    data = _prediction(season_db, race_id, PredictionTiming.RACE_DAY)
    is_same_race = training_data.ids[RACE_ID] == race_id
    expected = training_data.features[is_same_race].reset_index(drop=True)
    pd.testing.assert_frame_equal(data.features.reset_index(drop=True), expected)
