"""既存の予想のモデルの確率を、傾向の組の予測の列にする決まり。"""

from __future__ import annotations

from typing import Protocol

import numpy as np


class TendencyOutput(Protocol):
    """既存の予想の2つのモデルの確率の平均から、傾向の組の予測の列を作る。"""

    @property
    def columns(self) -> tuple[str, ...]:
        """作る列の名前。"""
        ...

    def of(self, probabilities: np.ndarray) -> dict[str, np.ndarray]:
        """列の名前 → 値。``probabilities`` は、二値なら行数ぶんの確率、多クラスなら 行数 × クラスの数。"""
        ...
