"""比べるモデルの作り方1つ。"""

from __future__ import annotations

from dataclasses import dataclass, replace

import pandas as pd

from yosou.shared.dataset import TrainingData
from yosou.shared.feature import PredictionTiming

#: 分けずに学ぶときの、区分の名前。
WHOLE = "全体"


@dataclass(frozen=True)
class ModelVariant:
    """比べるモデルの作り方1つ。

    - ``model``: 予想の名前（学習データの表の名前。例 ``longshots_in_top3``）。
    - ``key``: 予測を保存するファイルの名前（例 ``current``）。
    - ``name``: 表に出す名前（例 現行）。
    - ``columns``: 使う特徴量の列（当日の時点で使える列のうち）。
    - ``uses_baseline``: オッズから作った基準を出発点にして学ぶか。
    - ``segment_column``: 学習データを分ける評価用の列（穴馬の区分・人気帯）。None なら分けない。
    - ``timing``: 予測する時点（既定は当日）。
    """

    model: str
    key: str
    name: str
    columns: tuple[str, ...]
    uses_baseline: bool
    segment_column: str | None = None
    timing: PredictionTiming = PredictionTiming.RACE_DAY

    def prepare(self, data: TrainingData) -> TrainingData:
        """その時点の列にしてから、使う列だけにする。基準を使わない作り方では、基準を外す。"""
        timed = data.for_timing(self.timing)
        missing = [column for column in self.columns if column not in timed.features.columns]
        if missing:
            raise ValueError(f"{self.name}: 学習データに無い列があります: {'・'.join(missing)}")
        baseline = timed.baseline if self.uses_baseline else None
        return replace(timed, features=timed.features[list(self.columns)], baseline=baseline)

    def segments(self, data: TrainingData) -> list[str]:
        """学習データを分ける区分の名前（分けない作り方は「全体」だけ）。"""
        if self.segment_column is None:
            return [WHOLE]
        return sorted(str(value) for value in data.evaluation[self.segment_column].dropna().unique())

    def rows_of(self, data: TrainingData, segment: str) -> pd.Series:
        """その区分の行（真偽の列）。分けない作り方は全部の行。"""
        if self.segment_column is None:
            return pd.Series(True, index=data.ids.index)
        return data.evaluation[self.segment_column].astype(str).eq(segment)
