"""特徴量の型。"""

from __future__ import annotations

from enum import Enum


class FeatureKind(Enum):
    """特徴量の型。数値は大小に意味があり、カテゴリは種類を表す（設計書 02）。"""

    NUMERIC = "数値"
    CATEGORICAL = "カテゴリ"
