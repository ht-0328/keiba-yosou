"""LightGBM の設定。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LightGbmSettings:
    """LightGBM の設定（設計書 12 の 2）。

    - ``params``: ``LGBMClassifier`` の引数。書いたものがそのまま渡る。
    - ``early_stopping_rounds``: 検証データで、木を何本足しても良くならなければ止めるか。
    - ``min_category_count``: 学習データでの出走がこれより少ないカテゴリの値は「その他」にまとめる。
    """

    params: Mapping[str, Any]
    early_stopping_rounds: int
    min_category_count: int
