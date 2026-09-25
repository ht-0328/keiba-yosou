"""この予想の決めごとを渡して、共通の ``DatasetBuilder`` を組み立てる。"""

from __future__ import annotations

import duckdb

from yosou.shared.dataset import DatasetBuilder, HistoryRecordsLoader, RaceRecordsLoader
from yosou.shared.feature import FeatureBuilder
from yosou.shared.feature.group import (
    AptitudeFeatures,
    HorseFeatures,
    OddsFeatures,
    PedigreeFeatures,
    PeopleFeatures,
    PopularityHistoryFeatures,
    PreviousRunFeatures,
    RaceConditionFeatures,
    RecentFormFeatures,
    WorkoutFeatures,
)

from ..feature import CATALOG
from .favorite_only_selector import FavoriteOnlySelector
from .finish_group_labeler import FinishGroupLabeler

#: ``FeatureBuilder`` に渡すまとまり。手本の A〜I に、人気の履歴（J）と単勝オッズから見た評価（K）を足す。
#: 前走の人気は、手本のまとまり D にある。
_FEATURE_GROUPS = (
    RaceConditionFeatures(), HorseFeatures(), PeopleFeatures(), PreviousRunFeatures(),
    RecentFormFeatures(), AptitudeFeatures(), PedigreeFeatures(), WorkoutFeatures(),
    PopularityHistoryFeatures(), OddsFeatures(),
)


def dataset_builder(con: duckdb.DuckDBPyConnection) -> DatasetBuilder:
    """元DB への接続から、この予想の学習データ・予測用データを作るクラスを組み立てる。

    この予想の決めごとは3つ: 1番人気の行だけを入れる（``FavoriteOnlySelector``）、勝利・馬券内・馬券外の
    3つの列を付ける（``FinishGroupLabeler``）、特徴量は手本の A〜I に J・K を足す（``CATALOG``）。
    """
    return DatasetBuilder(
        HistoryRecordsLoader(con), RaceRecordsLoader(con),
        FavoriteOnlySelector(), FinishGroupLabeler(), FeatureBuilder(CATALOG, _FEATURE_GROUPS),
    )
