"""学習データ・予測用データの作り方（設計書 08・09・10）と、発走前の1レースの U（当日の使う傾き）の出し方。地方の合成DB だけを使う。"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from 共通 import db

from yosou.shared.dataset import RACE_DATE, RACE_ID, PredictionData, TrainingData
from yosou.shared.feature import PredictionTiming
from yosou.shared.tests import local_season as season
from yosou.upset_level.dataset import BetType, payout_column
from yosou.upset_level.feature import FAVORITE_ODDS, GOING

from ..dataset import LocalUpsetRule, local_race_dataset_builder
from ..feature import CATALOG, USED_SLOPE_NAMES, RaceUsedSlopes
from ..repository import PriorSlopeYearStore

#: 出馬表のレース（確定前なので DB にオッズが無い）に、手で渡す単勝オッズ。馬番が小さいほど人気。
CARD_ODDS: dict[int, float] = {horse_no: 1.5 + horse_no for horse_no in range(1, 9)}


def _prediction(path: Path, cache: Path, race_id: str, timing: PredictionTiming, odds: Mapping[int, float] | None = None) -> PredictionData:
    with db.open_db(path) as con:
        slopes = RaceUsedSlopes(con, PriorSlopeYearStore(cache)).of(race_id, timing)
        return local_race_dataset_builder(con, slopes).build_prediction_data(race_id, timing, odds=odds)


def test_学習データは1行1レースで_特徴量は中央の49個とUの2個(training_data: TrainingData):
    assert training_data.ids[RACE_DATE].min() >= pd.Timestamp(season.TRAIN_FIRST_DAY)
    assert training_data.ids[RACE_ID].is_unique
    assert list(training_data.features.columns) == list(CATALOG.names) and len(CATALOG.names) == 51
    assert list(training_data.features.columns[-2:]) == list(USED_SLOPE_NAMES)
    assert training_data.class_labels == (0, 1, 2, 3)
    # U は、先に終わったレースが無い日の最初のレースでも過去の傾きの表から入る
    assert training_data.features[list(USED_SLOPE_NAMES)].notna().mean().min() > 0.9


def test_目的変数は地方の線引きで付く(training_data: TrainingData):
    rule = LocalUpsetRule()
    for bet in BetType:
        yen = training_data.evaluation[payout_column(bet)].astype("float64")
        pd.testing.assert_series_equal(training_data.targets[bet.column_name], rule.levels_of(bet, yen), check_names=False)
    # 3連単は 1万円から中荒れ（中央の 2万円ではない）
    trifecta = training_data.evaluation[payout_column(BetType.TRIFECTA)].astype("float64")
    mid = training_data.targets[BetType.TRIFECTA.column_name] == 1
    assert trifecta[mid].between(10_000, 99_999).all()


@pytest.mark.parametrize(("timing", "columns"), [
    (PredictionTiming.RACE_DAY, 51), (PredictionTiming.DAY_BEFORE, 48), (PredictionTiming.THURSDAY, 27),
])
def test_予測用データは1行で_時点ごとに使う特徴量の数が変わる(local_season_db: Path, tmp_path: Path, timing: PredictionTiming, columns: int):
    data = _prediction(local_season_db, tmp_path, season.CARD_RACE_ID, timing, CARD_ODDS)
    assert len(data) == 1 and data.features.shape[1] == columns and data.timing is timing
    if timing is PredictionTiming.RACE_DAY:
        # 速報で出走取消になった馬番8 を除いた7頭。U の2列が入り、馬場状態は最後に発表された「重」
        assert data.features["出走頭数"].iloc[0] == 7 and data.features[FAVORITE_ODDS].iloc[0] == CARD_ODDS[1]
        assert data.features[GOING].iloc[0] == "重"
        assert data.features[list(USED_SLOPE_NAMES)].notna().all().all()
    else:
        assert not any(name in data.features.columns for name in USED_SLOPE_NAMES)


def test_発走前のレースの使う傾きは1行で_過去の傾きの表は年ごとにとっておく(local_season_db: Path, tmp_path: Path):
    # 確定前のレース（2025-01-11）の年の始まり。過去の傾きの表は、この日より前のレースだけで作る
    year_start = date(2025, 1, 1)
    store = PriorSlopeYearStore(tmp_path)
    with db.open_db(local_season_db) as con:
        slopes = RaceUsedSlopes(con, store).of(season.CARD_RACE_ID, PredictionTiming.RACE_DAY)
        table = store.load(con, year_start)
    assert list(slopes.index) == [season.CARD_RACE_ID] and list(slopes.columns) == list(USED_SLOPE_NAMES)
    assert np.isfinite(slopes.to_numpy()).all()
    # とっておいた表は 2025年1月1日より前のレースだけで作ったもので、2回目は読むだけ
    assert store.path(year_start).exists()
    assert table.as_of is not None and table.as_of < year_start
