"""この予想の部品を渡して、共通の ``DatasetBuilder``・``RaceDatasetBuilder`` を組み立てる。"""

from __future__ import annotations

import duckdb

from yosou.shared.dataset import DatasetBuilder, HistoryRecordsLoader, RaceDatasetBuilder, RaceRecordsLoader, RequiredInfoCheck
from yosou.shared.feature import FeatureBuilder, RaceConditionSummary, RaceFeatureBuilder
from yosou.shared.feature.group import (
    AptitudeFeatures,
    FieldComparisonFeatures,
    HorseFeatures,
    PedigreeFeatures,
    PeopleFeatures,
    PreviousRunFeatures,
    RaceConditionFeatures,
    RecentFormFeatures,
    WorkoutFeatures,
)
from yosou.shared.repository import RaceEarlyRecordRepository

from ..feature import (
    HORSE_CATALOG,
    RACE_CATALOG,
    ClosingFieldComparisonFeatures,
    ClosingHistoryFeatures,
    CourseShapeFeatures,
    EarlyFieldComparisonFeatures,
    EarlyHistoryFeatures,
    LateMaterialFeatures,
    PaceBaselineFeatures,
    PaceMaterialFeatures,
)
from ..feature.history import BASELINE_WINDOW_DAYS, FIRST_HALF_BASELINE, MEASURED_METERS, SECOND_HALF_BASELINE, STAGE
from . import label_names as names
from .early_runner_selector import EarlyRunnerSelector
from .horse_labeler import HorseLabeler
from .pace_record_source import PaceRecordSource
from .race_labeler import RaceLabeler

#: 1レースごとの学習データの評価用の列（学習データの列名 → レースごとの結果の表の列名）。
_RACE_EVALUATION_COLUMNS: dict[str, str] = {
    names.FIRST_HALF_TIME: "first3f", names.SECOND_HALF_TIME: "last3f_race",
    FIRST_HALF_BASELINE: FIRST_HALF_BASELINE, FIRST_HALF_BASELINE + STAGE: FIRST_HALF_BASELINE + STAGE,
    SECOND_HALF_BASELINE: SECOND_HALF_BASELINE, SECOND_HALF_BASELINE + STAGE: SECOND_HALF_BASELINE + STAGE,
    MEASURED_METERS: MEASURED_METERS,
}
#: 1レースごとの予測に要る情報と、取り込み方の案内（設計書 06 の図2）。
_RACE_GUIDANCE: dict[str, str] = {
    "馬場状態": "馬場状態がまだ DB にありません。jvstore realtime（開催日）で速報を取り込んでください。",
}


def horse_feature_builder() -> FeatureBuilder:
    """1頭ごとの特徴量（111個）を作るクラス。共通の A〜I に、K・M・N と、比べるまとまり L・O を足す。"""
    return FeatureBuilder(HORSE_CATALOG, (
        RaceConditionFeatures(), HorseFeatures(), PeopleFeatures(), PreviousRunFeatures(),
        RecentFormFeatures(), AptitudeFeatures(), PedigreeFeatures(), WorkoutFeatures(),
        EarlyHistoryFeatures(), CourseShapeFeatures(), ClosingHistoryFeatures(),
    ), field_groups=(FieldComparisonFeatures(), EarlyFieldComparisonFeatures(), ClosingFieldComparisonFeatures()))


def horse_dataset_builder(con: duckdb.DuckDBPyConnection) -> DatasetBuilder:
    """1頭ごとの学習データ・予測用データ（①②④⑤⑦）を作るクラス（設計書 04 の 1）。

    この予想の決めごとは3つ: 平地の出走馬を全頭入れる（``EarlyRunnerSelector``）、5つの目的変数をまとめて付ける
    （``HorseLabeler``）、レースごとの序盤と後半の記録（``race_history``）も読んで K〜O を作る。
    """
    history = RaceEarlyRecordRepository(con, BASELINE_WINDOW_DAYS)
    return DatasetBuilder(
        HistoryRecordsLoader(con, history), RaceRecordsLoader(con, history),
        EarlyRunnerSelector(), HorseLabeler(), horse_feature_builder(),
    )


def race_dataset_builder(con: duckdb.DuckDBPyConnection) -> RaceDatasetBuilder:
    """1レースごとの学習データ・予測用データ（③⑥）を作るクラス（設計書 04 の 1）。

    レースごとの結果は、前半・後半タイムとその基準（``PaceRecordSource``）。基準に3年を見るので、予測のときも
    予測するレースの 1095日前からのレースを読む。オッズは使わないので、単勝オッズの確かめはしない。
    """
    history = RaceEarlyRecordRepository(con, BASELINE_WINDOW_DAYS)
    race_features = RaceFeatureBuilder(RACE_CATALOG, horse_feature_builder(), (
        RaceConditionSummary(), PaceMaterialFeatures(), PaceBaselineFeatures(), LateMaterialFeatures(),
    ))
    return RaceDatasetBuilder(
        HistoryRecordsLoader(con, history), RaceRecordsLoader(con, history), PaceRecordSource(history),
        EarlyRunnerSelector(), RaceLabeler(), race_features, _RACE_EVALUATION_COLUMNS, names.THREE_CLASSES,
        RequiredInfoCheck(_RACE_GUIDANCE), history_days=BASELINE_WINDOW_DAYS, field_odds_check=None,
    )
