"""④荒れ具合の、1行 = 1レースの学習データの組み立て（地方の元DB と、中央の荒れ具合の予想の部品）。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from 共通.local_codes import LOCAL_FACTS_SOURCE

from yosou.local_form_aptitude_top3.feature import LOCAL_BASE_FEATURES
from yosou.local_form_aptitude_top3.repository import LOCAL_CAREER_LAYOUT
from yosou.local_track_bias import LocalBiasHistory
from yosou.shared.dataset import HistoryRecordsLoader, RaceDatasetBuilder, RaceRecordsLoader, RequiredInfoCheck, TrainingData, TrainingPeriod
from yosou.shared.feature import MARKET_FEATURES, FeatureBuilder, FeatureCatalog, PredictionTiming, RaceConditionSummary, RaceFeatureBuilder
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
from yosou.track_bias import BiasRunRepository
from yosou.upset_level.dataset import PAYOUT_COLUMNS, RaceSelector, UpsetLevel, UpsetLevelLabeler, UpsetLevelRule
from yosou.upset_level.feature import (
    RACE_FEATURES,
    ConditionUpsetRateFeatures,
    FavoriteRiskFeatures,
    FieldStrengthSpreadFeatures,
    OddsShapeFeatures,
)

from .used_slope_features import FEATURES as USED_SLOPE_FEATURES, UsedSlopeFeatures, race_slopes_table

#: 1頭ごとの特徴量の一覧（集約の元。地方の土台 A〜H ＋ J。調教は無い）。
HORSE_CATALOG = FeatureCatalog(LOCAL_BASE_FEATURES + MARKET_FEATURES)
#: 1頭ごとの ``FeatureBuilder`` に渡すまとまり（G 以外）。
_HORSE_FEATURE_GROUPS = (
    RaceConditionFeatures(LOCAL_CLASS_ORDER_FIXES), HorseFeatures(), PeopleFeatures(), PreviousRunFeatures(),
    RecentFormFeatures(), AptitudeFeatures(), PedigreeFeatures(), MarketFeatures(),
)
#: レース単位の特徴量の一覧: 中央の荒れ具合の 49個（A〜E）＋ 当日の馬場傾向のレースの値 2個（U）。
CATALOG = FeatureCatalog(RACE_FEATURES + USED_SLOPE_FEATURES)


def local_race_dataset_builder(con: duckdb.DuckDBPyConnection, rule: UpsetLevelRule, slopes_by_race: pd.DataFrame) -> RaceDatasetBuilder:
    """地方の元DB への接続と、レースごとの使う傾きの表（``race_slopes_table``）から、1行 = 1レースの学習データを作るクラスを組み立てる。"""
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
        PAYOUT_COLUMNS, UpsetLevel.class_labels(), RequiredInfoCheck({}),
    )


class LocalRaceTrainingDataCache:
    """④の学習データを作って ``folder`` に pickle で書く。同じ期間のファイルがあれば読むだけ。
    当日の馬場傾向のレースの値は、①と同じ年ごとのリーク防止（``LocalBiasHistory``）で作る。"""

    def __init__(self, folder: Path, rule: UpsetLevelRule) -> None:
        self._folder = Path(folder)
        self._rule = rule

    def path(self, period: TrainingPeriod) -> Path:
        return self._folder / f"荒れ具合の学習データ-{period.train_first_day.isoformat()}-{period.test_first_day.isoformat()}.pkl"

    def load_or_build(self, con_factory, period: TrainingPeriod) -> TrainingData:
        """``con_factory`` は元DB の接続を開くコンテキストマネージャを返す関数（``lambda: db.open_db(...)``）。"""
        path = self.path(period)
        if path.exists():
            return pd.read_pickle(path)
        with con_factory() as con:
            runs = BiasRunRepository(con).read(period.warmup_first_day)
            slopes = race_slopes_table(LocalBiasHistory().of(PredictionTiming.RACE_DAY, runs))
            data = local_race_dataset_builder(con, self._rule, slopes).build_training_data(period)
        self._folder.mkdir(parents=True, exist_ok=True)
        pd.to_pickle(data, path)
        return data
