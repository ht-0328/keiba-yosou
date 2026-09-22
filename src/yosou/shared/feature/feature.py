"""特徴量の一覧の1行。"""

from __future__ import annotations

from dataclasses import dataclass

from .feature_kind import FeatureKind
from .prediction_timing import PredictionTiming


@dataclass(frozen=True)
class Feature:
    """特徴量1つ。``name`` は学習データの列名にもなる。``group`` は設計書 09 のまとまり（A〜J）。

    ``known_from`` は、その特徴量が分かるようになる最初の時点（設計書 07）。省略すると木曜から分かる。
    枠番・馬番・馬場状態は前日から、馬体重は当日から、オッズは前日から、のように書く。
    """

    name: str
    group: str
    kind: FeatureKind
    known_from: PredictionTiming = PredictionTiming.THURSDAY

    @property
    def is_categorical(self) -> bool:
        return self.kind is FeatureKind.CATEGORICAL

    def is_known_at(self, timing: PredictionTiming) -> bool:
        """その時点で、この特徴量が分かっているか。"""
        return timing.is_at_or_after(self.known_from)
