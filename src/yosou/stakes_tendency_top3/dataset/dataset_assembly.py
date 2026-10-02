"""この予想の決めごとを渡して、共通の ``DatasetBuilder`` を組み立てる。"""

from __future__ import annotations

from pathlib import Path

import duckdb

from yosou.shared.dataset import (
    HISTORY_FIRST_DAY,
    AbilitySourcesLoader,
    DatasetBuilder,
    HistoryRecordsLoader,
    PoolProbabilityLoader,
    RaceRecordsLoader,
    Top3Baseline,
    Top3TargetBuilder,
)
from yosou.shared.feature import PEOPLE_WINDOW_DAYS, FeatureBuilder
from yosou.shared.feature.group import (
    AptitudeFeatures,
    HeadToHeadRatingFeatures,
    HorseAbilityFeatures,
    HorseFeatures,
    MarketFeatures,
    PedigreeFeatures,
    PeopleFeatures,
    PeopleMarketFeatures,
    PoolSupportFeatures,
    PreviousRunFeatures,
    RaceConditionFeatures,
    RecentFormFeatures,
    WorkoutFeatures,
)
from yosou.shared.repository import HeadToHeadRunRepository, MarketRunRepository, StakesTendencyRepository
from yosou.shared.repository.speed_figure_repository import DEFAULT_FOLDER

from ..feature import ABILITY_CATALOG, RACE_DAY_ABILITY_FEATURES, RACE_DAY_CATALOG, StakesTendencyFeatures
from .runner_selector import RunnerSelector

#: 当日のモデルのまとまり（手本の当日と同じ A〜F・H・I・J・L・N と、M のうち名前の重ならない列）に、この予想の K を足す。
_RACE_DAY_FEATURE_GROUPS = (
    RaceConditionFeatures(), HorseFeatures(), PeopleFeatures(), PreviousRunFeatures(),
    RecentFormFeatures(), AptitudeFeatures(), PedigreeFeatures(), WorkoutFeatures(),
    MarketFeatures(), PeopleMarketFeatures(), PoolSupportFeatures(),
    HorseAbilityFeatures(tuple(feature.name for feature in RACE_DAY_ABILITY_FEATURES)),
    StakesTendencyFeatures(),
)
#: 木曜・前日のモデルのまとまり（手本と同じ M・O・J）に K を足す。G（同じレースの馬との比較）は使わない（手本と同じ）。
_ABILITY_FEATURE_GROUPS = (HorseAbilityFeatures(), HeadToHeadRatingFeatures(), MarketFeatures(), StakesTendencyFeatures())


def ability_dataset_builder(con: duckdb.DuckDBPyConnection, figure_folder: Path = DEFAULT_FOLDER) -> DatasetBuilder:
    """木曜・前日のモデルの学習データ・予測用データを作るクラス（M・O・J に K を足した ``ABILITY_CATALOG``）。

    この予想の決めごとは、**重賞の出走だけ**を入れる（``RunnerSelector``）、3着以内なら 1（共通の ``Top3TargetBuilder``）、
    手本の木曜・前日の材料に K（重賞の傾向）を足すこと。K の元になる傾向は ``StakesTendencyRepository`` が読んで
    ``EntryRecords.stakes_tendency`` に入る。M の元の記録は ``AbilitySourcesLoader`` で、O（対戦レーティング）の元の記録は
    ``HeadToHeadRunRepository`` で読む（手本と同じ）
    （``figure_folder`` はスピード指数をとっておく場所。テストでは一時フォルダを渡す）。
    前日は、オッズから見た3着以内率（``Top3Baseline``）を出発点にして、上げ下げだけを学ぶ（手本と同じ。木曜は基準なし）。
    """
    sources, runs = AbilitySourcesLoader(con, figure_folder), HeadToHeadRunRepository(con, HISTORY_FIRST_DAY)
    return DatasetBuilder(
        HistoryRecordsLoader(con, stakes_tendency=StakesTendencyRepository(con), ability_sources=sources, head_to_head_runs=runs),
        RaceRecordsLoader(con, stakes_tendency=StakesTendencyRepository(con), ability_sources=sources, head_to_head_runs=runs),
        RunnerSelector(), Top3TargetBuilder(),
        FeatureBuilder(ABILITY_CATALOG, _ABILITY_FEATURE_GROUPS, field_groups=()),
        baseline=Top3Baseline(),
    )


def race_day_dataset_builder(con: duckdb.DuckDBPyConnection, figure_folder: Path = DEFAULT_FOLDER) -> DatasetBuilder:
    """当日のモデルの学習データ・予測用データを作るクラス（手本の当日の 285個に K を足した ``RACE_DAY_CATALOG``）。

    ローダーには、手本の当日と同じ L の過去の全出走（``MarketRunRepository``）・券種ごとのオッズから見た確率
    （``PoolProbabilityLoader``）・M の元の記録（``AbilitySourcesLoader``）に、重賞の傾向（``StakesTendencyRepository``）を足して渡す。
    行の選び方・目的変数・基準は ``ability_dataset_builder`` と同じ。
    """
    pools, sources = PoolProbabilityLoader(con), AbilitySourcesLoader(con, figure_folder)
    return DatasetBuilder(
        HistoryRecordsLoader(con, stakes_tendency=StakesTendencyRepository(con), market_runs=_market_runs(con),
                             ability_sources=sources, pool_probabilities=pools),
        RaceRecordsLoader(con, stakes_tendency=StakesTendencyRepository(con), market_runs=_market_runs(con),
                          ability_sources=sources, pool_probabilities=pools),
        RunnerSelector(), Top3TargetBuilder(), FeatureBuilder(RACE_DAY_CATALOG, _RACE_DAY_FEATURE_GROUPS),
        baseline=Top3Baseline(),
    )


def _market_runs(con: duckdb.DuckDBPyConnection) -> MarketRunRepository:
    """L（騎手・調教師・血統の市場に対する成績）の材料の、過去の全出走を読むリポジトリ。"""
    return MarketRunRepository(con, PEOPLE_WINDOW_DAYS)
