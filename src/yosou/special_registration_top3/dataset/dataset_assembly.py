"""この予想の決めごとを渡して、共通の ``DatasetBuilder`` を組み立てる。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb

from yosou.shared.dataset import (
    HISTORY_FIRST_DAY,
    AbilitySourcesLoader,
    DatasetBuilder,
    HistoryRecordsLoader,
    RunnerSelector,
    Top3TargetBuilder,
)
from yosou.shared.feature import FeatureBuilder
from yosou.shared.feature.group import HeadToHeadRatingFeatures, HorseAbilityFeatures
from yosou.shared.repository import HeadToHeadRunRepository
from yosou.shared.repository.speed_figure_repository import DEFAULT_FOLDER

from ..feature import BASE_CATALOG, REGISTRATION_ABILITY_NAMES, SpecialRaceFeatures
from ..repository import RegistrationEntryTableRepository
from .registration_cutoff import RegistrationCutoff
from .registration_records_loader import RegistrationRecordsLoader

#: 学習データの既定の期間（設計書 08 の 4）。ウォームアップは DB にある最初の年、学習は 2012年から（中央の馬の力の材料と同じ）。
WARMUP_FIRST_DAY = date(2011, 1, 1)
TRAIN_FIRST_DAY = date(2012, 1, 1)
#: 事実表の開催日の列（材料の締めの日の式に渡す）。
_RACE_DATE = "race_date"


def registration_dataset_builder(con: duckdb.DuckDBPyConnection, figure_folder: Path = DEFAULT_FOLDER) -> DatasetBuilder:
    """元DB への接続から、この予想の学習データ・予測用データを作るクラスを組み立てる（設計書 04）。

    この予想の決めごとは、特徴量の一覧（``BASE_CATALOG``。M のうち特別登録の時点に分かる 168個・O の7個・Y の1個。T は
    ``AbilityScoreAttachment`` があとで足す）、学習の対象に材料の締めの日（登録日相当。``RegistrationCutoff``）の列を足すこと、
    予測用の記録を特別登録の登録馬の行から集めること（``RegistrationRecordsLoader``）。
    行の選び方（出走した全頭）・目的変数（3着以内なら 1）は中央の予想と同じ共通の部品。基準（オッズのロジット）は無い。
    M の元の記録は ``AbilitySourcesLoader``、O の元の記録は ``HeadToHeadRunRepository`` が読む。
    ``figure_folder`` はスピード指数をとっておく場所（テストでは一時フォルダを渡す）。
    """
    cutoff_sql = RegistrationCutoff().sql(_RACE_DATE)
    sources = AbilitySourcesLoader(con, figure_folder)
    runs = HeadToHeadRunRepository(con, HISTORY_FIRST_DAY)
    groups = (HorseAbilityFeatures(REGISTRATION_ABILITY_NAMES), HeadToHeadRatingFeatures(), SpecialRaceFeatures())
    return DatasetBuilder(
        HistoryRecordsLoader(con, ability_sources=sources, head_to_head_runs=runs, as_of_sql=cutoff_sql),
        RegistrationRecordsLoader(con, RegistrationEntryTableRepository(con, cutoff_sql), sources, runs),
        RunnerSelector(), Top3TargetBuilder(), FeatureBuilder(BASE_CATALOG, groups, field_groups=()),
    )
