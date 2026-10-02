"""1つの予想モデルを、一括予測の入口から扱うための値。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import duckdb

from yosou.shared.dataset import DatasetBuilder, RaceDatasetBuilder

from .batch_predictor import BatchPredictor

#: 保存済みモデルの置き場（``reports/<予想の名前>/models``。予想モデルの ``CommonArguments`` と同じ）。
_MODELS_FOLDER = "models"


@dataclass(frozen=True)
class PredictionSource:
    """1つの予想モデルの「学習データを作る工場」と「予測する部品の作り方」を束ねた値。

    - ``name``: 予想のパッケージ名。出力の CSV は ``<name>.csv``。
    - ``label``: 人が読む名前。
    - ``models_folder``: 予想の名前（各パッケージの ``YOSOU_NAME``）。保存済みモデルは ``<reports>/<models_folder>/models``。
    - ``builder_factory``: 元DB への接続から、その予想の ``DatasetBuilder``（か ``RaceDatasetBuilder``）を組み立てる関数。
    - ``predictor_factory``: モデルの置き場（``<reports>/<models_folder>/models``）から、その予想の ``BatchPredictor`` を作る関数。
    """

    name: str
    label: str
    models_folder: str
    builder_factory: Callable[[duckdb.DuckDBPyConnection], DatasetBuilder | RaceDatasetBuilder]
    predictor_factory: Callable[[Path], BatchPredictor]

    def models_root(self, reports_root: Path) -> Path:
        """保存済みモデルの置き場。"""
        return Path(reports_root) / self.models_folder / _MODELS_FOLDER

    def predictor(self, reports_root: Path) -> BatchPredictor:
        """その置き場のモデルで予測する部品。"""
        return self.predictor_factory(self.models_root(reports_root))
