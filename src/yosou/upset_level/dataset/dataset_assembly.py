"""この予想の決めごとを渡して、共通の ``RaceDatasetBuilder`` を組み立てる。"""

from __future__ import annotations

import duckdb

from yosou.shared.dataset import (
    HistoryRecordsLoader,
    RaceDatasetBuilder,
    RaceRecordsLoader,
    RequiredInfoCheck,
)
from yosou.shared.feature import FeatureBuilder, RaceFeatureBuilder
from yosou.shared.feature.group import (
    AptitudeFeatures,
    HorseFeatures,
    MarketFeatures,
    PedigreeFeatures,
    PeopleFeatures,
    PreviousRunFeatures,
    RaceConditionFeatures,
    RecentFormFeatures,
    WorkoutFeatures,
)
from yosou.shared.repository import RacePayoutRepository

from ..feature import (
    CATALOG,
    FAVORITE_ODDS,
    FAVORITE_WEIGHT_CHANGE,
    GOING,
    HORSE_CATALOG,
    ConditionUpsetRateFeatures,
    FavoriteRiskFeatures,
    FieldStrengthSpreadFeatures,
    OddsShapeFeatures,
    RaceConditionSummary,
)
from .race_column_names import PAYOUT_COLUMNS
from .race_selector import RaceSelector
from .upset_level import UpsetLevel
from .upset_level_labeler import UpsetLevelLabeler
from .upset_level_rule import UpsetLevelRule

#: 1頭ごとの ``FeatureBuilder`` に渡すまとまり（G 以外）。共通の A〜F・H・I に、オッズの J を足す。
_HORSE_FEATURE_GROUPS = (
    RaceConditionFeatures(), HorseFeatures(), PeopleFeatures(), PreviousRunFeatures(),
    RecentFormFeatures(), AptitudeFeatures(), PedigreeFeatures(), WorkoutFeatures(),
    MarketFeatures(),
)
#: その時点で使うのに DB にまだ無いと予測できないレース単位の特徴量と、取り込み方の案内（設計書 06 の図2）。
_GUIDANCE: dict[str, str] = {
    GOING: "馬場状態がまだ DB にありません。jvstore realtime（開催日）で速報を取り込んでください。",
    FAVORITE_ODDS: "単勝オッズがまだ DB にありません。--odds 馬番:オッズ で全頭ぶん渡すか、"
                   "jvstore realtime（開催日）で締め切り前のオッズを取り込んでください。",
    FAVORITE_WEIGHT_CHANGE: "馬体重がまだ DB にありません。"
                            "馬体重の発表のあとに jvstore realtime（開催日）で速報を取り込んでください。",
}


def race_dataset_builder(con: duckdb.DuckDBPyConnection) -> RaceDatasetBuilder:
    """元DB への接続から、この予想の学習データ・予測用データを作るクラスを組み立てる。

    この予想の決めごとは4つ: 平地の出走馬を全頭入れる（``RaceSelector``）、券種ごとの払戻を線引きで4段階にする
    （``UpsetLevelRule``・``UpsetLevelLabeler``）、1頭ごとの特徴量（A〜I と J）をまとまり A〜E に集約する
    （``CATALOG`` と5つのまとまり）、評価用の列に4券種の払戻を残す（``PAYOUT_COLUMNS``）。
    """
    rule = UpsetLevelRule()
    horse_features = FeatureBuilder(HORSE_CATALOG, _HORSE_FEATURE_GROUPS)
    race_features = RaceFeatureBuilder(CATALOG, horse_features, (
        RaceConditionSummary(), OddsShapeFeatures(), FieldStrengthSpreadFeatures(),
        FavoriteRiskFeatures(), ConditionUpsetRateFeatures(rule),
    ))
    return RaceDatasetBuilder(
        HistoryRecordsLoader(con), RaceRecordsLoader(con), RacePayoutRepository(con),
        RaceSelector(), UpsetLevelLabeler(rule), race_features,
        PAYOUT_COLUMNS, UpsetLevel.class_labels(), RequiredInfoCheck(_GUIDANCE),
    )
