"""まとまり M（複勝オッズから見た評価。設計書 09 の M）の作り方と、学習データ・時点ごとの列。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from yosou.shared.dataset import TrainingData
from yosou.shared.feature import EntryRecords, PredictionTiming, WorkoutCoverage

from ..feature import (
    CATALOG,
    PLACE_MARKET_RATE,
    PLACE_ODDS_FEATURES,
    PLACE_ODDS_HIGH_FEATURE,
    PLACE_ODDS_LOW_FEATURE,
    PLACE_TO_WIN_RATIO,
    PlaceMarketRate,
    PlaceOddsFeatures,
)

M_NAMES = [feature.name for feature in PLACE_ODDS_FEATURES]


def _race(race_id: str, lows: list[float | None], highs: list[float | None], win_odds: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"race_id": race_id, "place_odds_low": lows, "place_odds_high": highs, "win_odds": win_odds})


def _records(entries: pd.DataFrame) -> EntryRecords:
    empty = pd.DataFrame()
    return EntryRecords(entries, empty, empty, WorkoutCoverage.complete(), empty, empty, empty, empty)


def test_place_market_rate_sums_to_the_paid_places_in_each_race():
    # 8頭立ては3着まで、7頭立ては2着まで当たりなので、真ん中のオッズの逆数をそれぞれ合計 3・2 にそろえる
    eight = _race("A", [2.0] * 8, [4.0] * 8, [5.0] * 8)
    seven = _race("B", [2.0] * 7, [4.0] * 7, [5.0] * 7)
    rate = PlaceMarketRate().of(pd.concat([eight, seven], ignore_index=True))
    np.testing.assert_allclose(rate[:8], 3 / 8)
    np.testing.assert_allclose(rate[8:], 2 / 7)


def test_place_market_rate_ranks_by_the_middle_odds_and_skips_missing_horses():
    entries = _race("A", [1.1, 3.0, 9.0, None, 5.0, 5.0, 5.0, 5.0], [1.3, 5.0, 15.0, None, 9.0, 9.0, 9.0, 9.0],
                    [1.5, 5.0, 20.0, 50.0, 10.0, 10.0, 10.0, 10.0])
    rate = PlaceMarketRate().of(entries)
    # 複勝オッズの無い馬は欠損値で、そろえる合計にも入れない。1 を超えた値は 1 にする
    assert rate.isna().tolist() == [False, False, False, True, False, False, False, False]
    assert rate.iloc[0] == pytest.approx(1.0) and rate.iloc[1] > rate.iloc[2]


def test_place_odds_features_hold_the_odds_the_rate_and_the_ratio_to_the_win_market():
    entries = _race("A", [1.5, 2.0, 3.0, 6.0, 8.0, 10.0, 15.0, 20.0], [2.0, 3.0, 5.0, 9.0, 12.0, 16.0, 25.0, 40.0],
                    [2.5, 4.0, 6.0, 12.0, 20.0, 30.0, 50.0, 80.0])
    features = PlaceOddsFeatures().build(_records(entries))
    assert list(features.columns) == M_NAMES and features.index.equals(entries.index)
    assert features[PLACE_ODDS_LOW_FEATURE].tolist() == entries["place_odds_low"].tolist()
    assert features[PLACE_ODDS_HIGH_FEATURE].tolist() == entries["place_odds_high"].tolist()
    # 比 = 複勝オッズから見た3着以内率 ÷ 単勝オッズから見た3着以内率（どちらも正なので、比も正）
    assert (features[PLACE_TO_WIN_RATIO] > 0).all() and features[PLACE_MARKET_RATE].between(0, 1).all()


def test_place_odds_features_are_missing_without_the_odds():
    # 木曜（馬番が無い）や複勝オッズを取り込んでいない馬は、欠損値になる
    entries = _race("A", [None] * 8, [None] * 8, [np.nan] * 8)
    assert PlaceOddsFeatures().build(_records(entries)).isna().all().all()


def test_the_catalog_uses_m_from_the_day_before():
    assert all(name in CATALOG.names for name in M_NAMES) and len(CATALOG.names) == 86
    assert not set(M_NAMES) & set(CATALOG.columns_for(PredictionTiming.THURSDAY))
    assert set(M_NAMES) <= set(CATALOG.columns_for(PredictionTiming.DAY_BEFORE))


def test_training_data_has_the_place_odds_features(training_data: TrainingData):
    # 合成DB に足した複勝オッズ（確定の断面）から、全部の穴馬に M が付く
    assert training_data.features[M_NAMES].notna().all().all()
    assert (training_data.features[PLACE_ODDS_HIGH_FEATURE] > training_data.features[PLACE_ODDS_LOW_FEATURE]).all()
