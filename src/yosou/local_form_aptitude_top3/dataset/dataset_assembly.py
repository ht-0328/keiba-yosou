"""地方の決めごとを渡して、共通の ``DatasetBuilder`` を組み立てる。"""

from __future__ import annotations

from datetime import date

import duckdb

from 共通.local_codes import LOCAL_FACTS_SOURCE

from yosou.shared.dataset import (
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
    HorseFeatures,
    MarketFeatures,
    PedigreeFeatures,
    PeopleFeatures,
    PeopleMarketFeatures,
    PoolSupportFeatures,
    PreviousRunFeatures,
    RaceConditionFeatures,
    RecentFormFeatures,
)
from yosou.shared.feature.group.race_condition_features import LOCAL_CLASS_ORDER_FIXES
from yosou.shared.repository import CareerCountRepository, HeadToHeadRunRepository, MarketRunRepository

from ..feature import CATALOG
from ..repository import LOCAL_CAREER_LAYOUT

#: 学習データの既定の期間（設計書 08 の 4）。ウォームアップは DB にある最初の年から、学習は 2019年から。
LOCAL_WARMUP_FIRST_DAY = date(2016, 1, 1)
LOCAL_TRAIN_FIRST_DAY = date(2019, 1, 1)
#: 対戦レーティング（O）の元の記録（過去の全出走の着順）を読み始める日。DB にある最初の年。
LOCAL_HISTORY_FIRST_DAY = date(2016, 1, 1)
#: ``FeatureBuilder`` に渡すまとまり（G 以外）。中央の今の材料から調教（I）を除き、クラスの付け直しを地方の決まりにした A〜H に、
#: J（市場の評価）・L（市場に対する成績）・O（対戦レーティング）・N（券種の支持）・Q（勝ち切る材料）を足す（設計書 09）。
_FEATURE_GROUPS = (
    RaceConditionFeatures(LOCAL_CLASS_ORDER_FIXES), HorseFeatures(), PeopleFeatures(), PreviousRunFeatures(),
    RecentFormFeatures(), AptitudeFeatures(), PedigreeFeatures(),
    MarketFeatures(), PeopleMarketFeatures(), HeadToHeadRatingFeatures(), PoolSupportFeatures(), FinishPowerFeatures(),
)


def local_dataset_builder(con: duckdb.DuckDBPyConnection) -> DatasetBuilder:
    """元DB（nvdata-store）への接続から、この予想の学習データ・予測用データを作るクラスを組み立てる（設計書 04）。

    地方の決めごとは、事実表の元データ（``LOCAL_FACTS_SOURCE``。競馬場 30〜61・競走馬マスタ地方の血統・競走条件名称から読むクラス）、
    出走別着度数地方（``nd``）の欄（``LOCAL_CAREER_LAYOUT``）、特徴量の一覧（``CATALOG``。96個）、クラスの並び順の付け直し。
    行の選び方（出走した全頭）・目的変数（3着以内なら 1）・基準（オッズから見た3着以内率。前日から）は中央の予想と同じ共通の部品。
    ローダーには、L の過去の全出走（``MarketRunRepository``）・N の券種ごとの確率（``PoolProbabilityLoader``）・
    O の過去の全出走の着順（``HeadToHeadRunRepository``）・Q の元の記録（``FinishRecordsLoader``）を渡す。
    学習データは1つで、各時点のモデルにはその時点で使う列だけを渡す（設計書 07）。
    """
    market_runs = MarketRunRepository(con, PEOPLE_WINDOW_DAYS)
    pools = PoolProbabilityLoader(con)
    head_to_head_runs = HeadToHeadRunRepository(con, LOCAL_HISTORY_FIRST_DAY)
    finishes = FinishRecordsLoader(con)
    career_counts = CareerCountRepository(con, LOCAL_CAREER_LAYOUT)
    return DatasetBuilder(
        HistoryRecordsLoader(con, market_runs=market_runs, pool_probabilities=pools, head_to_head_runs=head_to_head_runs,
                             finish_records=finishes, facts_source=LOCAL_FACTS_SOURCE, career_counts=career_counts),
        RaceRecordsLoader(con, market_runs=market_runs, pool_probabilities=pools, head_to_head_runs=head_to_head_runs,
                          finish_records=finishes, facts_source=LOCAL_FACTS_SOURCE, career_counts=career_counts),
        RunnerSelector(), Top3TargetBuilder(), FeatureBuilder(CATALOG, _FEATURE_GROUPS),
        baseline=Top3Baseline(),
    )
