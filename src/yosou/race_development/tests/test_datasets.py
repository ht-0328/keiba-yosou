"""学習データ（1頭ごと・1レースごと）の形と、目的変数の付き方を確かめる。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import RACE_ID

from ..dataset import label_names as names
from ..feature import HORSE_CATALOG, RACE_CATALOG
from ..workflow import KindDatasets


def test_horse_data_has_all_groups(datasets: KindDatasets) -> None:
    horses = datasets.horses
    assert list(horses.features.columns) == list(HORSE_CATALOG.names)
    assert horses.features["先頭率"].notna().all()
    assert horses.features["近5走の序盤の位置の平均"].notna().mean() > 0.5
    assert horses.features["近5走の上がりの速さの平均"].notna().mean() > 0.5
    assert horses.features["最初のコーナーの番号"].dropna().eq(3).all()


def test_leader_label_is_one_horse_per_race(datasets: KindDatasets) -> None:
    targets, race = datasets.horses.targets, datasets.horses.ids[RACE_ID]
    labeled = targets[names.LEADER].notna()
    leaders = targets.loc[labeled, names.LEADER].groupby(race[labeled]).sum()
    assert labeled.any()
    assert leaders.eq(1).all()


def test_late_labels_are_between_zero_and_one(datasets: KindDatasets) -> None:
    targets = datasets.horses.targets
    for column in (names.CORNER4_POSITION, names.CLOSING_SPEED, names.EARLY_POSITION):
        values = targets[column].dropna()
        assert values.between(0, 1).all()
        assert len(values) > 0


def test_winner_label_is_one_horse_per_race(datasets: KindDatasets) -> None:
    targets, race = datasets.horses.targets, datasets.horses.ids[RACE_ID]
    labeled = targets[names.WINNER].notna()
    assert targets.loc[labeled, names.WINNER].groupby(race[labeled]).sum().eq(1).all()


def test_race_data_has_pace_labels(datasets: KindDatasets) -> None:
    races = datasets.races
    assert list(races.features.columns) == list(RACE_CATALOG.names)
    pace = races.targets[names.PACE_CLASS].dropna()
    assert set(pace.unique()) <= {0.0, 1.0, 2.0}
    assert races.targets[names.SECOND_HALF_DIFF].notna().any()
    assert pd.to_numeric(races.features["前半タイムの基準"], errors="coerce").notna().any()
