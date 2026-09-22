"""特徴量の一覧の1行。"""

from __future__ import annotations

from dataclasses import dataclass

from .feature_kind import FeatureKind


@dataclass(frozen=True)
class Feature:
    """特徴量1つ。``name`` は学習データの列名にもなる。``group`` は設計書 09 のまとまり（A〜I）。"""

    name: str
    group: str
    kind: FeatureKind

    @property
    def is_categorical(self) -> bool:
        return self.kind is FeatureKind.CATEGORICAL
