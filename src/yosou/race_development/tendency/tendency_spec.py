"""展開の予想の材料にする、1つの既存の予想の決めごと。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import duckdb

from yosou.shared.dataset import DatasetBuilder, RaceDatasetBuilder
from yosou.shared.feature import PredictionTiming

from .tendency_unit import TendencyUnit


@dataclass(frozen=True)
class TendencySpec:
    """1つの既存の予想の決めごと。

    - ``label``: 表に出す名前。
    - ``per_race``: 1行 = 1レースの予想か（False なら 1行 = 1頭）。
    - ``builder``: 元DB への接続から、既存の予想の学習データ・予測用データを作るクラスを組み立てる関数（既存の予想のもの）。
    - ``timings``: 予測を出す時点。既存の予想がモデルを持たない時点は、その列を欠損値にする。
    - ``units``: 別々に学ぶモデル（区分・券種ごと）。
    """

    label: str
    per_race: bool
    builder: Callable[[duckdb.DuckDBPyConnection], DatasetBuilder | RaceDatasetBuilder]
    timings: tuple[PredictionTiming, ...]
    units: tuple[TendencyUnit, ...]
