"""この予想の決めごとを渡して、共通の ``DatasetBuilder`` を組み立てる。"""

from __future__ import annotations

import duckdb

from yosou.shared.dataset import DatasetBuilder, HistoryRecordsLoader, RaceRecordsLoader
from yosou.shared.feature import EntryColumns, FeatureBuilder
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
from .column_names import FAVORITE_BAND
from .favorite_rule import FavoriteRule
from .favorite_selector import FavoriteSelector
from .out_of_top3_baseline import OutOfTop3Baseline
from .out_of_top3_target_builder import OutOfTop3TargetBuilder

#: ``FeatureBuilder`` に渡すまとまり（G 以外）。共通の A〜F・H・I に、共通の J（人気の履歴）と K（単勝オッズ）を足す。
_FEATURE_GROUPS = (
    RaceConditionFeatures(), HorseFeatures(), PeopleFeatures(), PreviousRunFeatures(),
    RecentFormFeatures(), AptitudeFeatures(), PedigreeFeatures(), WorkoutFeatures(),
    PopularityHistoryFeatures(), OddsFeatures(),
)
#: 出走の行から、学習データの評価用の列と予測の結果に残す列（人気帯。帯ごとに学ぶのと、出力の表に使う）。
_EXTRA_COLUMNS = EntryColumns({FAVORITE_BAND: FAVORITE_BAND})


def dataset_builder(con: duckdb.DuckDBPyConnection) -> DatasetBuilder:
    """元DB への接続から、この予想の学習データ・予測用データを作るクラスを組み立てる。

    この予想の決めごとは3つ: 人気馬の行だけを入れる（``FavoriteSelector``）、4着以下なら 1
    （``OutOfTop3TargetBuilder``）、特徴量に まとまり J を足す（``CATALOG`` と ``_FEATURE_GROUPS``）。
    ほかの予想は、同じ ``DatasetBuilder`` に別のクラスを渡す（設計書 04）。

    オッズから見た4着以下の確率（``OutOfTop3Baseline``）を出発点にして、「同じオッズの馬より負けやすいか」だけを学ぶ
    （既存モデルの修正計画の 1「人気馬の4着以下」）。基準は人気馬に絞る前の全頭のオッズで作る。
    """
    return DatasetBuilder(
        HistoryRecordsLoader(con), RaceRecordsLoader(con),
        FavoriteSelector(FavoriteRule()), OutOfTop3TargetBuilder(),
        FeatureBuilder(CATALOG, _FEATURE_GROUPS), _EXTRA_COLUMNS, baseline=OutOfTop3Baseline(),
    )
