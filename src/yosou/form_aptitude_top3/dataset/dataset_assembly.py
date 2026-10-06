"""この予想の決めごとを渡して、共通の ``DatasetBuilder`` を組み立てる。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb

from yosou.shared.dataset import (
    HISTORY_FIRST_DAY,
    AbilitySourcesLoader,
    DatasetBuilder,
    FinishRecordsLoader,
    HistoryRecordsLoader,
    PoolProbabilityLoader,
    RaceRecordsLoader,
    RunnerSelector,
    Top3Baseline,
    Top3TargetBuilder,
)
from yosou.shared.feature import PEOPLE_WINDOW_DAYS, FeatureBuilder
from yosou.shared.feature.group import (
    AptitudeFeatures,
    FinishPowerFeatures,
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
from yosou.shared.repository import HeadToHeadRunRepository, MarketRunRepository
from yosou.shared.repository.speed_figure_repository import DEFAULT_FOLDER

from ..feature import ABILITY_CATALOG, CATALOG, POOL_CATALOG, RACE_DAY_ABILITY_FEATURES, RACE_DAY_WIN_CATALOG


#: 馬の力の材料のモデルの学習データの始まり。研究「一番人気を疑う」で、2017年からより長い期間で学ぶほうが良かった
#: （ウォームアップは前の年の 2011年。DB にある最初の年）。
ABILITY_TRAIN_FIRST_DAY = date(2012, 1, 1)
#: ``FeatureBuilder`` に渡すまとまり（G 以外）。共通の A〜F・H・I に、この予想の J と L を足す。
_FEATURE_GROUPS = (
    RaceConditionFeatures(), HorseFeatures(), PeopleFeatures(), PreviousRunFeatures(),
    RecentFormFeatures(), AptitudeFeatures(), PedigreeFeatures(), WorkoutFeatures(),
    MarketFeatures(), PeopleMarketFeatures(),
)
#: 今の材料に N（券種ごとのオッズから見た支持）を足したまとまり。
_POOL_FEATURE_GROUPS = (*_FEATURE_GROUPS, PoolSupportFeatures())
#: 当日のモデルのまとまり（今の材料・N と、M のうち今の材料と名前の重ならない列と、1着のモデルだけが使う Q）。
_RACE_DAY_FEATURE_GROUPS = (
    *_POOL_FEATURE_GROUPS, HorseAbilityFeatures(tuple(feature.name for feature in RACE_DAY_ABILITY_FEATURES)), FinishPowerFeatures(),
)
#: 馬の力の材料のまとまり（M と O と J）。G（同じレースの馬との比較）は A〜F の特徴量から作るので、使わない。
_ABILITY_FEATURE_GROUPS = (HorseAbilityFeatures(), HeadToHeadRatingFeatures(), MarketFeatures())


def _market_runs(con: duckdb.DuckDBPyConnection) -> MarketRunRepository:
    """L（騎手・調教師・血統の市場に対する成績）の材料の、過去の全出走を読むリポジトリ。"""
    return MarketRunRepository(con, PEOPLE_WINDOW_DAYS)


def dataset_builder(con: duckdb.DuckDBPyConnection) -> DatasetBuilder:
    """元DB への接続から、今の材料（A〜L の 79個）の学習データ・予測用データを作るクラスを組み立てる。

    この予想の決めごとは3つ: 出走した全頭を入れる（``RunnerSelector``）、3着以内なら 1（共通の ``Top3TargetBuilder``）、
    特徴量は A〜I の 71個にまとまり J（市場の評価）の4個と L（騎手・調教師・血統の市場に対する成績）の4個を足した 79個
    （``CATALOG`` と ``_FEATURE_GROUPS``）。L の材料の過去の全出走は ``MarketRunRepository`` で読む。
    ほかの予想は、同じ ``DatasetBuilder`` に別のクラスを渡す（設計書 04）。当日に券種のオッズが無いときのモデルは、
    この 79個で学ぶ。展開の予想と研究も、この学習データを使う。

    オッズが分かる前日・当日は、オッズから見た3着以内率（``Top3Baseline``）を出発点にして、近走や適性による
    上げ下げだけを学ぶ（既存モデルの修正計画の 1「全出走馬の3着以内」）。
    """
    return DatasetBuilder(
        HistoryRecordsLoader(con, market_runs=_market_runs(con)), RaceRecordsLoader(con, market_runs=_market_runs(con)),
        RunnerSelector(), Top3TargetBuilder(), FeatureBuilder(CATALOG, _FEATURE_GROUPS),
        baseline=Top3Baseline(),
    )


def pool_dataset_builder(con: duckdb.DuckDBPyConnection) -> DatasetBuilder:
    """今の材料に N（券種ごとのオッズから見た支持の6個）を足した学習データ・予測用データを作るクラス（研究の比べに使う。本番の当日のモデルは ``race_day_dataset_builder``）。

    券種ごとのオッズから見た確率は
    ``PoolProbabilityLoader`` で読む（終わったレースは確定、これから走るレースは締め切り前の最新の断面）。
    """
    pools = PoolProbabilityLoader(con)
    return DatasetBuilder(
        HistoryRecordsLoader(con, market_runs=_market_runs(con), pool_probabilities=pools),
        RaceRecordsLoader(con, market_runs=_market_runs(con), pool_probabilities=pools),
        RunnerSelector(), Top3TargetBuilder(), FeatureBuilder(POOL_CATALOG, _POOL_FEATURE_GROUPS),
        baseline=Top3Baseline(),
    )


def race_day_dataset_builder(con: duckdb.DuckDBPyConnection, figure_folder: Path = DEFAULT_FOLDER) -> DatasetBuilder:
    """当日のモデルの学習データ・予測用データを作るクラス（今の材料に N と M を足した 285個に、1着のモデルだけが使う Q の 10個を足した
    ``RACE_DAY_WIN_CATALOG``。3着以内のモデルに渡す前に ``FinishPowerFreeData`` で Q を外す）。

    ローダーには、L の過去の全出走（``MarketRunRepository``）・券種ごとのオッズから見た確率（``PoolProbabilityLoader``）・
    M の元の記録（``AbilitySourcesLoader``）・Q の元の記録（``FinishRecordsLoader``）を渡す。``figure_folder`` はスピード指数をとっておく場所。
    """
    pools, sources, finishes = PoolProbabilityLoader(con), AbilitySourcesLoader(con, figure_folder), FinishRecordsLoader(con)
    return DatasetBuilder(
        HistoryRecordsLoader(con, market_runs=_market_runs(con), ability_sources=sources, pool_probabilities=pools, finish_records=finishes),
        RaceRecordsLoader(con, market_runs=_market_runs(con), ability_sources=sources, pool_probabilities=pools, finish_records=finishes),
        RunnerSelector(), Top3TargetBuilder(), FeatureBuilder(RACE_DAY_WIN_CATALOG, _RACE_DAY_FEATURE_GROUPS),
        baseline=Top3Baseline(),
    )


def ability_dataset_builder(con: duckdb.DuckDBPyConnection, figure_folder: Path = DEFAULT_FOLDER) -> DatasetBuilder:
    """馬の力の材料（M の 202個と O の7個と J の4個）の学習データ・予測用データを作るクラス（木曜・前日のモデル）。

    M の元の記録（過去の全出走・スピード指数・調教のまとめ・セリの取引）は ``AbilitySourcesLoader`` で、O（対戦レーティング）の
    元の記録（2011年からの平地の全出走の着順）は ``HeadToHeadRunRepository`` で読む。
    ``figure_folder`` はスピード指数をとっておく場所（テストでは一時フォルダを渡す）。
    行の選び方・目的変数・基準は ``dataset_builder`` と同じ（基準はオッズの分かる前日から）。
    """
    sources, runs = AbilitySourcesLoader(con, figure_folder), HeadToHeadRunRepository(con, HISTORY_FIRST_DAY)
    return DatasetBuilder(
        HistoryRecordsLoader(con, ability_sources=sources, head_to_head_runs=runs),
        RaceRecordsLoader(con, ability_sources=sources, head_to_head_runs=runs),
        RunnerSelector(), Top3TargetBuilder(), FeatureBuilder(ABILITY_CATALOG, _ABILITY_FEATURE_GROUPS, field_groups=()),
        baseline=Top3Baseline(),
    )
