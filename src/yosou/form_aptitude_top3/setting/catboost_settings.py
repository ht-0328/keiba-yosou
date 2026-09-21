"""CatBoost の設定。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CatBoostSettings:
    """CatBoost の設定（設計書 13 の 2）。

    - ``params``: ``CatBoostClassifier`` の引数。書いたものがそのまま渡る。
    - ``early_stopping_rounds``: 検証データで、木を何本足しても良くならなければ止めるか。
    """

    params: Mapping[str, Any]
    early_stopping_rounds: int
