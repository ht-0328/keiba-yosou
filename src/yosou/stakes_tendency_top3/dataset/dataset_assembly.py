"""この予想の決めごとを渡して、共通の ``DatasetBuilder`` を組み立てる。"""

from __future__ import annotations

import duckdb

from yosou.shared.dataset import DatasetBuilder, HistoryRecordsLoader, RaceRecordsLoader, Top3Baseline, Top3TargetBuilder
from yosou.shared.feature import FeatureBuilder
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
from yosou.shared.repository import StakesTendencyRepository

from ..feature import CATALOG, StakesTendencyFeatures
from .runner_selector import RunnerSelector

#: ``FeatureBuilder`` に渡すまとまり（G 以外）。共通の A〜F・H・I に、J（市場の評価）と、この予想の K を足す。
_FEATURE_GROUPS = (
    RaceConditionFeatures(), HorseFeatures(), PeopleFeatures(), PreviousRunFeatures(),
    RecentFormFeatures(), AptitudeFeatures(), PedigreeFeatures(), WorkoutFeatures(),
    MarketFeatures(), StakesTendencyFeatures(),
)


def dataset_builder(con: duckdb.DuckDBPyConnection) -> DatasetBuilder:
    """元DB への接続から、この予想の学習データ・予測用データを作るクラスを組み立てる。

    この予想の決めごとは4つ: **重賞の出走だけ**を入れる（``RunnerSelector``）、3着以内なら 1
    （共通の ``Top3TargetBuilder``）、特徴量は A〜J の 75個に K（重賞の傾向）の 10個を足した 85個、
    K の元になる傾向は ``StakesTendencyRepository`` が読んで ``EntryRecords.stakes_tendency`` に入る。
    前日・当日は、オッズから見た3着以内率（``Top3Baseline``）を出発点にして、上げ下げだけを学ぶ（手本と同じ）。
    """
    return DatasetBuilder(
        HistoryRecordsLoader(con, stakes_tendency=StakesTendencyRepository(con)),
        RaceRecordsLoader(con, stakes_tendency=StakesTendencyRepository(con)),
        RunnerSelector(), Top3TargetBuilder(), FeatureBuilder(CATALOG, _FEATURE_GROUPS),
        baseline=Top3Baseline(),
    )
