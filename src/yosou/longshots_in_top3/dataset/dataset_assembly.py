"""この予想の決めごとを渡して、共通の ``DatasetBuilder`` を組み立てる。"""

from __future__ import annotations

import duckdb

from yosou.shared.dataset import DatasetBuilder, HistoryRecordsLoader, RaceRecordsLoader, Top3Baseline, Top3TargetBuilder
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
from .column_names import LONGSHOT_ZONE
from .longshot_rule import LongshotRule
from .longshot_selector import LongshotSelector

#: ``FeatureBuilder`` に渡すまとまり（G 以外）。共通の A〜F・H・I に、共通の J（人気の履歴）と K（単勝オッズ）を足す。
_FEATURE_GROUPS = (
    RaceConditionFeatures(), HorseFeatures(), PeopleFeatures(), PreviousRunFeatures(),
    RecentFormFeatures(), AptitudeFeatures(), PedigreeFeatures(), WorkoutFeatures(),
    PopularityHistoryFeatures(), OddsFeatures(),
)
#: 出走の行から、学習データの評価用の列と予測の結果に残す列（穴馬の区分。設計書 08 の 2）。
_EXTRA_COLUMNS = EntryColumns({LONGSHOT_ZONE: LONGSHOT_ZONE})


def dataset_builder(con: duckdb.DuckDBPyConnection) -> DatasetBuilder:
    """元DB への接続から、この予想の学習データ・予測用データを作るクラスを組み立てる。

    この予想の決めごとは3つ: 穴馬の行だけを入れ、区分の列を足す（``LongshotSelector``）、3着以内なら 1
    （共通の ``Top3TargetBuilder``）、特徴量に まとまり J を足す（``CATALOG`` と ``_FEATURE_GROUPS``）。
    ほかの予想は、同じ ``DatasetBuilder`` に別のクラスを渡す（設計書 04）。

    オッズが分かる前日・当日は、オッズから見た3着以内率（``Top3Baseline``）を出発点にして、近走や適性による
    上げ下げだけを学ぶ（既存モデルの修正計画の 1「穴馬の3着以内」）。基準は穴馬に絞る前の全頭のオッズで作る。
    """
    return DatasetBuilder(
        HistoryRecordsLoader(con), RaceRecordsLoader(con),
        LongshotSelector(LongshotRule()), Top3TargetBuilder(),
        FeatureBuilder(CATALOG, _FEATURE_GROUPS), _EXTRA_COLUMNS, baseline=Top3Baseline(),
    )
