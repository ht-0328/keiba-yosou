"""1つの予想の、学習データの作り方。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import duckdb

from yosou.shared.dataset import DatasetBuilder, RaceDatasetBuilder
from yosou.shared.feature import FeatureCatalog


@dataclass(frozen=True)
class ModelTableSpec:
    """1つの予想の学習データの作り方。

    - ``name``: 予想のパッケージ名（保存するフォルダの名前にも使う。例 ``form_aptitude_top3``）。
    - ``label``: 人が読む名前（例 近走と適性から3着以内を予想）。
    - ``builder_factory``: 元DB への接続から、その予想の ``DatasetBuilder``（荒れ具合は ``RaceDatasetBuilder``）を作る関数。
    - ``catalog``: その予想の特徴量の一覧（保存した表を読み戻すときに使う）。
    - ``class_labels``: 目的変数の値の並び（二値分類は (0, 1)、荒れ具合は (0, 1, 2, 3)）。
    """

    name: str
    label: str
    builder_factory: Callable[[duckdb.DuckDBPyConnection], DatasetBuilder | RaceDatasetBuilder]
    catalog: FeatureCatalog
    class_labels: tuple[int, ...] = (0, 1)
