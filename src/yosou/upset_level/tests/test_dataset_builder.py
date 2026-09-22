"""学習データ・予測用データの作り方（設計書 06 の図1・08・09・10）。"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from 共通 import db

from yosou.shared.dataset import (
    FAVORITE_FINISH,
    FAVORITE_ODDS as FINAL_FAVORITE_ODDS,
    FIELD_SIZE as FINAL_FIELD_SIZE,
    RACE_DATE,
    RACE_ID,
    UPPER_MAX_ODDS as FINAL_UPPER_MAX_ODDS,
    PredictionData,
    TrainingData,
)
from yosou.shared.feature import PredictionTiming
from yosou.shared.tests import synthetic_season as season

from ..dataset import BetType, UpsetLevelRule, payout_column, race_dataset_builder
from ..feature import CATALOG, FAVORITE_ODDS, GOING, course_rate_name

#: 出馬表のレース（確定前なので DB にオッズが無い）に、手で渡す単勝オッズ。馬番が小さいほど人気。
CARD_ODDS: dict[int, float] = {horse_no: 1.5 + horse_no for horse_no in range(1, 9)}


def _prediction(path: Path, race_id: str, timing: PredictionTiming,
                odds: Mapping[int, float] | None = None) -> PredictionData:
    with db.open_db(path) as con:
        return race_dataset_builder(con).build_prediction_data(race_id, timing, odds=odds)


def test_training_data_has_one_row_per_flat_race_from_the_train_first_day(training_data: TrainingData):
    assert training_data.ids[RACE_DATE].min() >= pd.Timestamp(season.TRAIN_FIRST_DAY)
    assert training_data.ids[RACE_ID].is_unique
    assert set(training_data.features["芝ダ"]) == {"芝", "ダート"}
    assert list(training_data.features.columns) == list(CATALOG.names) and len(CATALOG.names) == 49
    assert training_data.class_labels == (0, 1, 2, 3)
    assert training_data.features.index.equals(training_data.ids.index)


def test_targets_follow_the_payouts_and_the_thresholds(training_data: TrainingData):
    rule = UpsetLevelRule()
    for bet in BetType:
        yen = training_data.evaluation[payout_column(bet)].astype("float64")
        expected = rule.levels_of(bet, yen)
        actual = training_data.targets[bet.column_name]
        assert actual.dropna().isin([0, 1, 2, 3]).all()
        pd.testing.assert_series_equal(actual, expected, check_names=False)
    # 架空のシーズンは人気薄が来るほど払戻が高いので、どの券種にも4つのクラスが全部出る
    assert set(training_data.targets[BetType.TRIFECTA.column_name].dropna()) == {0, 1, 2, 3}


def test_with_label_drops_rows_without_that_label(training_data: TrainingData):
    labeled = training_data.with_label(BetType.TRIFECTA.column_name)
    assert labeled.label_name == BetType.TRIFECTA.column_name and labeled.label.notna().all()
    assert 0 < len(labeled) <= len(training_data)
    with pytest.raises(ValueError, match="目的変数の列"):
        training_data.with_label("荒れ具合（複勝）")


def test_race_level_features_are_aggregated_from_the_field(training_data: TrainingData):
    features = training_data.features
    evaluation = training_data.evaluation
    # 出走頭数は出走した馬の数、1番人気のオッズは全頭の最小、市場勝率の合計は 1 以下
    assert (features["出走頭数"] == evaluation[FINAL_FIELD_SIZE]).all()
    assert (features[FAVORITE_ODDS] == evaluation[FINAL_FAVORITE_ODDS]).all()
    assert (features["2〜5番人気の最大オッズ"] == evaluation[FINAL_UPPER_MAX_ODDS]).all()
    assert features["市場勝率の上位3頭の合計"].between(0, 1).all()
    assert features["市場勝率のエントロピー"].between(0, 1).all()
    assert features["前走が無い馬の割合"].between(0, 1).all()
    assert features["特別戦か"].isin(["はい", "いいえ"]).all() and features["ハンデ戦か"].isin(["はい", "いいえ"]).all()


def test_favorite_features_come_from_the_lowest_odds_horse(training_data: TrainingData):
    # 1番人気の確定着順は評価用の列にある（1番人気が競走中止なら着順なし）。特徴量の「1番人気の…」はその馬の前走までの値
    assert training_data.evaluation[FINAL_FAVORITE_ODDS].notna().all()
    assert training_data.evaluation[FAVORITE_FINISH].notna().mean() > 0.9
    assert training_data.features["1番人気の乗り替わり"].dropna().isin(["継続", "乗り替わり", "前走なし"]).all()
    assert training_data.features["1番人気の通算の出走数"].notna().all()


def test_past_upset_rates_use_only_earlier_races(training_data: TrainingData):
    rate = training_data.features[course_rate_name(BetType.TRIFECTA)]
    assert rate.dropna().between(0, 1).all() and rate.notna().any()
    # 最初の開催日のレースは、ウォームアップ期間のレースから荒れ率を数えられる
    is_first_day = training_data.ids[RACE_DATE] == training_data.ids[RACE_DATE].min()
    assert rate[is_first_day].notna().any()


@pytest.mark.parametrize(("timing", "columns"), [
    (PredictionTiming.RACE_DAY, 49), (PredictionTiming.DAY_BEFORE, 48),
])
def test_prediction_data_of_a_card_has_one_row(season_db: Path, timing: PredictionTiming, columns: int):
    data = _prediction(season_db, season.CARD_RACE_ID, timing, CARD_ODDS)
    assert len(data) == 1 and data.features.shape[1] == columns and data.timing is timing
    # 速報で出走取消になった馬番8 を除いた7頭。馬場状態は、最後に発表された「重」
    assert data.features["出走頭数"].iloc[0] == 7 and data.features[GOING].iloc[0] == "重"
    assert data.features[FAVORITE_ODDS].iloc[0] == CARD_ODDS[1]
    assert data.features["単勝10倍未満の頭数"].iloc[0] == 7


def test_race_day_prediction_uses_the_favorites_announced_weight(season_db: Path):
    data = _prediction(season_db, season.CARD_RACE_ID, PredictionTiming.RACE_DAY, CARD_ODDS)
    # 馬番1（オッズ最小）は奇数なので、速報の馬体重の増減は −1kg
    assert data.features["1番人気の馬体重の増減"].iloc[0] == -1


def test_thursday_prediction_works_before_horse_numbers_and_odds(season_db: Path):
    data = _prediction(season_db, season.ENTRY_LIST_RACE_ID, PredictionTiming.THURSDAY)
    assert len(data) == 1 and data.features.shape[1] == 27
    assert FAVORITE_ODDS not in data.features.columns and GOING not in data.features.columns


def test_day_before_prediction_needs_all_odds(season_db: Path):
    with pytest.raises(ValueError, match="--odds"):
        _prediction(season_db, season.CARD_RACE_ID, PredictionTiming.DAY_BEFORE)
    with pytest.raises(ValueError, match="分からない馬が"):
        _prediction(season_db, season.CARD_RACE_ID, PredictionTiming.DAY_BEFORE, {1: 2.0, 2: 3.0})


def test_jump_races_are_not_predicted(season_db: Path):
    with pytest.raises(ValueError, match="障害"):
        _prediction(season_db, season.JUMP_CARD_RACE_ID, PredictionTiming.RACE_DAY)


def test_prediction_of_a_finished_race_matches_training_features(
        season_db: Path, training_data: TrainingData):
    # 学習データと予測用データを同じ作り方で作るので、終わったレースを予測用に作り直しても特徴量は同じになる
    race_id = training_data.ids[RACE_ID].iloc[-1]
    data = _prediction(season_db, race_id, PredictionTiming.RACE_DAY)
    expected = training_data.features[training_data.ids[RACE_ID] == race_id].reset_index(drop=True)
    pd.testing.assert_frame_equal(data.features.reset_index(drop=True), expected)
    assert not np.isnan(data.features[FAVORITE_ODDS].iloc[0])
