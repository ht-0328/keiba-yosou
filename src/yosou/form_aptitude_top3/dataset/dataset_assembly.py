"""この予想の決めごとを渡して、共通の ``DatasetBuilder`` を組み立てる。"""

from __future__ import annotations

import duckdb

from yosou.shared.dataset import DatasetBuilder, HistoryRecordsLoader, RaceRecordsLoader, Top3TargetBuilder
from yosou.shared.feature import FeatureBuilder
from yosou.shared.feature.group import (
    AptitudeFeatures,
    HorseFeatures,
    PedigreeFeatures,
    PeopleFeatures,
    PreviousRunFeatures,
    RaceConditionFeatures,
    RecentFormFeatures,
    WorkoutFeatures,
)

from ..feature import CATALOG, MarketFeatures
from .runner_selector import RunnerSelector

#: ``FeatureBuilder`` に渡すまとまり（G 以外）。共通の A〜F・H・I に、この予想の J を足す。
_FEATURE_GROUPS = (
    RaceConditionFeatures(), HorseFeatures(), PeopleFeatures(), PreviousRunFeatures(),
    RecentFormFeatures(), AptitudeFeatures(), PedigreeFeatures(), WorkoutFeatures(),
    MarketFeatures(),
)


def dataset_builder(con: duckdb.DuckDBPyConnection) -> DatasetBuilder:
    """元DB への接続から、この予想の学習データ・予測用データを作るクラスを組み立てる。

    この予想の決めごとは3つ: 出走した全頭を入れる（``RunnerSelector``）、3着以内なら 1（共通の ``Top3TargetBuilder``）、
    特徴量は A〜I の 71個にまとまり J（市場の評価）の3個を足した 74個（``CATALOG`` と ``_FEATURE_GROUPS``）。
    ほかの予想は、同じ ``DatasetBuilder`` に別のクラスを渡す（設計書 04）。
    """
    return DatasetBuilder(
        HistoryRecordsLoader(con), RaceRecordsLoader(con),
        RunnerSelector(), Top3TargetBuilder(), FeatureBuilder(CATALOG, _FEATURE_GROUPS),
    )
