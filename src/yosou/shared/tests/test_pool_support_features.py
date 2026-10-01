"""まとまり N（券種ごとのオッズから見た支持）の作り方。DB を使わず、手で作った記録を渡して確かめる。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ..feature import POOL_SUPPORT_FEATURES, POOL_SUPPORT_NAMES, EntryRecords, WorkoutCoverage
from ..feature.group import PoolSupportFeatures
from ..feature.odds import TOP3_RATE, WIN_RATE, MarketPlaces
from ..repository import POOLS


def _records(pools: pd.DataFrame) -> EntryRecords:
    """3頭立ての1レース（単勝 2.0・4.0・8.0 倍）と、券種の確率の表。"""
    entries = pd.DataFrame({"race_id": ["r1"] * 3, "horse_no": [1, 2, 3], "win_odds": [2.0, 4.0, 8.0]})
    return EntryRecords(
        entries=entries, past_runs=pd.DataFrame(), workouts=pd.DataFrame(), workout_coverage=WorkoutCoverage.complete(),
        jockey_days=pd.DataFrame(), trainer_days=pd.DataFrame(), sire_days=pd.DataFrame(), damsire_days=pd.DataFrame(),
        pool_probabilities=pools,
    )


def test_the_six_features_are_numbers_in_group_n_known_on_race_day():
    assert [feature.name for feature in POOL_SUPPORT_FEATURES] == list(POOL_SUPPORT_NAMES)
    assert len(POOL_SUPPORT_NAMES) == len(POOLS) == 6
    assert all(feature.group == "N" and feature.known_from.value == "race_day" for feature in POOL_SUPPORT_FEATURES)


def test_support_is_the_log_ratio_of_pool_and_win_probabilities():
    pools = pd.DataFrame({"race_id": ["r1"] * 3, "horse_no": [1, 2, 3],
                          **{spec.column: [0.5, 0.3, 0.2] for spec in POOLS}})
    records = _records(pools)
    features = PoolSupportFeatures().build(records)
    market = MarketPlaces().of(records.entries)
    trifecta = POOL_SUPPORT_NAMES[0]
    trio = POOL_SUPPORT_NAMES[2]
    # 3連単は単勝から見た勝率と、3連複は単勝から見た3着以内率と比べる
    np.testing.assert_allclose(features[trifecta], np.log([0.5, 0.3, 0.2]) - np.log(market[WIN_RATE]))
    np.testing.assert_allclose(features[trio], np.log([0.5, 0.3, 0.2]) - np.log(market[TOP3_RATE]))


def test_support_is_missing_without_pool_odds():
    features = PoolSupportFeatures().build(_records(pd.DataFrame()))
    assert features.isna().all().all() and list(features.columns) == list(POOL_SUPPORT_NAMES)


def test_support_is_missing_for_a_horse_without_pool_odds():
    pools = pd.DataFrame({"race_id": ["r1"] * 2, "horse_no": [1, 2], **{spec.column: [0.6, 0.4] for spec in POOLS}})
    features = PoolSupportFeatures().build(_records(pools))
    assert features.iloc[2].isna().all() and features.iloc[0].notna().all()
    assert features.iloc[0, 0] == pytest.approx(np.log(0.6) - np.log(MarketPlaces().of(_records(pools).entries)[WIN_RATE][0]))
