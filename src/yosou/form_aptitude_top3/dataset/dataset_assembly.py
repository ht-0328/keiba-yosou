"""この予想の決めごとを渡して、共通の ``DatasetBuilder`` を組み立てる。"""

from __future__ import annotations

import duckdb

from yosou.shared.dataset import DatasetBuilder, HistoryRecordsLoader, RaceRecordsLoader, Top3Baseline, Top3TargetBuilder
from yosou.shared.feature import PEOPLE_WINDOW_DAYS, FeatureBuilder
from yosou.shared.feature.group import (
    AptitudeFeatures,
    HorseFeatures,
    MarketFeatures,
    PedigreeFeatures,
    PeopleFeatures,
    PeopleMarketFeatures,
    PreviousRunFeatures,
    RaceConditionFeatures,
    RecentFormFeatures,
    WorkoutFeatures,
)
from yosou.shared.repository import MarketRunRepository

from ..feature import CATALOG
from .runner_selector import RunnerSelector

#: ``FeatureBuilder`` に渡すまとまり（G 以外）。共通の A〜F・H・I に、この予想の J と L を足す。
_FEATURE_GROUPS = (
    RaceConditionFeatures(), HorseFeatures(), PeopleFeatures(), PreviousRunFeatures(),
    RecentFormFeatures(), AptitudeFeatures(), PedigreeFeatures(), WorkoutFeatures(),
    MarketFeatures(), PeopleMarketFeatures(),
)


def _market_runs(con: duckdb.DuckDBPyConnection) -> MarketRunRepository:
    """L（騎手・調教師・血統の市場に対する成績）の材料の、過去の全出走を読むリポジトリ。"""
    return MarketRunRepository(con, PEOPLE_WINDOW_DAYS)


def dataset_builder(con: duckdb.DuckDBPyConnection) -> DatasetBuilder:
    """元DB への接続から、この予想の学習データ・予測用データを作るクラスを組み立てる。

    この予想の決めごとは3つ: 出走した全頭を入れる（``RunnerSelector``）、3着以内なら 1（共通の ``Top3TargetBuilder``）、
    特徴量は A〜I の 71個にまとまり J（市場の評価）の4個と L（騎手・調教師・血統の市場に対する成績）の4個を足した 79個
    （``CATALOG`` と ``_FEATURE_GROUPS``）。L の材料の過去の全出走は ``MarketRunRepository`` で読む。
    ほかの予想は、同じ ``DatasetBuilder`` に別のクラスを渡す（設計書 04）。

    オッズが分かる前日・当日は、オッズから見た3着以内率（``Top3Baseline``）を出発点にして、近走や適性による
    上げ下げだけを学ぶ（既存モデルの修正計画の 1「全出走馬の3着以内」）。
    """
    return DatasetBuilder(
        HistoryRecordsLoader(con, market_runs=_market_runs(con)), RaceRecordsLoader(con, market_runs=_market_runs(con)),
        RunnerSelector(), Top3TargetBuilder(), FeatureBuilder(CATALOG, _FEATURE_GROUPS),
        baseline=Top3Baseline(),
    )
