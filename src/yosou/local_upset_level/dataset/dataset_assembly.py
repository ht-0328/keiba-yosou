"""地方の決めごとを渡して、共通の ``RaceDatasetBuilder`` を組み立てる。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from 共通.local_codes import LOCAL_FACTS_SOURCE

from yosou.local_form_aptitude_top3.repository import LOCAL_CAREER_LAYOUT
from yosou.shared.dataset import HistoryRecordsLoader, RaceDatasetBuilder, RaceRecordsLoader, RequiredInfoCheck
from yosou.shared.feature import FeatureBuilder, RaceConditionSummary, RaceFeatureBuilder
from yosou.shared.feature.group import (
    AptitudeFeatures,
    HorseFeatures,
    MarketFeatures,
    PedigreeFeatures,
    PeopleFeatures,
    PreviousRunFeatures,
    RaceConditionFeatures,
    RecentFormFeatures,
)
from yosou.shared.feature.group.race_condition_features import LOCAL_CLASS_ORDER_FIXES
from yosou.shared.repository import CareerCountRepository, RacePayoutRepository
from yosou.upset_level.dataset import PAYOUT_COLUMNS, RaceSelector, UpsetLevel, UpsetLevelLabeler, UpsetLevelRule
from yosou.upset_level.feature import (
    FAVORITE_ODDS,
    FAVORITE_WEIGHT_CHANGE,
    GOING,
    ConditionUpsetRateFeatures,
    FavoriteRiskFeatures,
    FieldStrengthSpreadFeatures,
    OddsShapeFeatures,
)

from ..feature import CATALOG, HORSE_CATALOG, UsedSlopeFeatures
from .local_upset_rule import LocalUpsetRule

#: 学習データの既定の期間（設計書 08 の 4）。地方の全頭の予想と同じ（ウォームアップは DB にある最初の年、学習は 2019年から）。
LOCAL_UPSET_WARMUP_FIRST_DAY = date(2016, 1, 1)
LOCAL_UPSET_TRAIN_FIRST_DAY = date(2019, 1, 1)
#: 1頭ごとの ``FeatureBuilder`` に渡すまとまり（G 以外）。地方の土台 A〜H（調教は無い。クラスの付け直しは地方の決まり）に、オッズの J を足す。
_HORSE_FEATURE_GROUPS = (
    RaceConditionFeatures(LOCAL_CLASS_ORDER_FIXES), HorseFeatures(), PeopleFeatures(), PreviousRunFeatures(),
    RecentFormFeatures(), AptitudeFeatures(), PedigreeFeatures(), MarketFeatures(),
)
#: その時点で使うのに DB にまだ無いと予測できないレース単位の特徴量と、取り込み方の案内（中央と同じ3つ。取り込む道具は nvstore）。
_GUIDANCE: dict[str, str] = {
    GOING: "馬場状態がまだ DB にありません。nvstore realtime（開催日）で速報を取り込んでください。",
    FAVORITE_ODDS: "単勝オッズがまだ DB にありません。--odds 馬番:オッズ で全頭ぶん渡すか、"
                   "nvstore realtime（開催日）で締め切り前のオッズを取り込んでください。",
    FAVORITE_WEIGHT_CHANGE: "馬体重がまだ DB にありません。"
                            "馬体重の発表のあとに nvstore realtime（開催日）で速報を取り込んでください。",
}


def local_race_dataset_builder(con: duckdb.DuckDBPyConnection, slopes_by_race: pd.DataFrame,
                               rule: UpsetLevelRule | None = None) -> RaceDatasetBuilder:
    """地方の元DB への接続と、レースごとの使う傾きの表（``race_slopes_table``。学習は全レース、予測は対象の1レース）から、
    1行 = 1レースの学習データ・予測用データを作るクラスを組み立てる（設計書 04）。

    地方の決めごとは4つ: 事実表の元データ（``LOCAL_FACTS_SOURCE``）と出走別着度数地方の欄（``LOCAL_CAREER_LAYOUT``）、
    線引き（``LocalUpsetRule``。省略時）、特徴量の一覧（``CATALOG``。中央の 49個 ＋ U 2個）、当日の馬場傾向のレースの値（``UsedSlopeFeatures``）。
    行の選び方・目的変数の付け方・評価用の列は中央の荒れ具合の予想と同じ部品。
    """
    rule = rule or LocalUpsetRule()
    career_counts = CareerCountRepository(con, LOCAL_CAREER_LAYOUT)
    horse_features = FeatureBuilder(HORSE_CATALOG, _HORSE_FEATURE_GROUPS)
    race_features = RaceFeatureBuilder(CATALOG, horse_features, (
        RaceConditionSummary(), OddsShapeFeatures(), FieldStrengthSpreadFeatures(), FavoriteRiskFeatures(),
        ConditionUpsetRateFeatures(rule), UsedSlopeFeatures(slopes_by_race),
    ))
    return RaceDatasetBuilder(
        HistoryRecordsLoader(con, facts_source=LOCAL_FACTS_SOURCE, career_counts=career_counts),
        RaceRecordsLoader(con, facts_source=LOCAL_FACTS_SOURCE, career_counts=career_counts),
        RacePayoutRepository(con), RaceSelector(), UpsetLevelLabeler(rule), race_features,
        PAYOUT_COLUMNS, UpsetLevel.class_labels(), RequiredInfoCheck(_GUIDANCE),
    )
