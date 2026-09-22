"""この予想の決めごとを渡して、共通の ``DatasetBuilder`` を組み立てる。"""

from __future__ import annotations

import duckdb

from yosou.shared.dataset import DatasetBuilder, HistoryRecordsLoader, RaceRecordsLoader
from yosou.shared.feature import FeatureBuilder
from yosou.shared.feature.group import (
    AptitudeFeatures,
    HorseFeatures,
    PedigreeFeatures,
    PeopleFeatures,
    PopularityHistoryFeatures,
    PreviousRunFeatures,
    RaceConditionFeatures,
    RecentFormFeatures,
    WorkoutFeatures,
)

from ..feature import CATALOG
from .favorite_rule import FavoriteRule
from .favorite_selector import FavoriteSelector
from .out_of_top3_target_builder import OutOfTop3TargetBuilder

#: ``FeatureBuilder`` に渡すまとまり（G 以外）。共通の A〜F・H・I に、共通の J を足す。
_FEATURE_GROUPS = (
    RaceConditionFeatures(), HorseFeatures(), PeopleFeatures(), PreviousRunFeatures(),
    RecentFormFeatures(), AptitudeFeatures(), PedigreeFeatures(), WorkoutFeatures(),
    PopularityHistoryFeatures(),
)


def dataset_builder(con: duckdb.DuckDBPyConnection) -> DatasetBuilder:
    """元DB への接続から、この予想の学習データ・予測用データを作るクラスを組み立てる。

    この予想の決めごとは3つ: 人気馬の行だけを入れる（``FavoriteSelector``）、4着以下なら 1
    （``OutOfTop3TargetBuilder``）、特徴量に まとまり J を足す（``CATALOG`` と ``_FEATURE_GROUPS``）。
    ほかの予想は、同じ ``DatasetBuilder`` に別のクラスを渡す（設計書 04）。
    """
    return DatasetBuilder(
        HistoryRecordsLoader(con), RaceRecordsLoader(con),
        FavoriteSelector(FavoriteRule()), OutOfTop3TargetBuilder(),
        FeatureBuilder(CATALOG, _FEATURE_GROUPS),
    )
