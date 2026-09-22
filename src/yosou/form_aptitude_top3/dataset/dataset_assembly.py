"""この予想の決めごとを渡して、共通の ``DatasetBuilder`` を組み立てる。"""

from __future__ import annotations

import duckdb

from yosou.shared.dataset import DatasetBuilder, HistoryRecordsLoader, RaceRecordsLoader
from yosou.shared.feature import FeatureBuilder

from ..feature import CATALOG
from .runner_selector import RunnerSelector
from .target_builder import TargetBuilder


def dataset_builder(con: duckdb.DuckDBPyConnection) -> DatasetBuilder:
    """元DB への接続から、この予想の学習データ・予測用データを作るクラスを組み立てる。

    この予想の決めごとは3つ: 出走した全頭を入れる（``RunnerSelector``）、3着以内なら 1（``TargetBuilder``）、
    特徴量は 71個（``CATALOG``）。ほかの予想は、同じ ``DatasetBuilder`` に別のクラスを渡す（設計書 04）。
    """
    return DatasetBuilder(
        HistoryRecordsLoader(con), RaceRecordsLoader(con),
        RunnerSelector(), TargetBuilder(), FeatureBuilder(CATALOG),
    )
