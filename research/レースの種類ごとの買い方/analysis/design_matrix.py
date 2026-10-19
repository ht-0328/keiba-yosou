"""組の表から、重みを掛ける行列（もとと、もと × 種類の印）を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .race_kinds import KIND_DUMMIES
from .weight_method import WeightMethod


class DesignMatrix:
    """案（``WeightMethod``）のもとの列と、``with_kinds`` なら「もと × 種類の印」の列を並べた行列を作る。

    ``penalized`` は、罰則を掛ける列（種類の差の列）なら真。最初の列は必ずその券種自身の市場の対数（推定の出発点に使う）。
    例: もと2つ（a, b）・印1つ（d）なら、列は a・b・a×d・b×d で、罰則は 偽・偽・真・真。
    """

    def __init__(self, method: WeightMethod, dtype: type = np.float64) -> None:
        self._method = method
        self._dtype = dtype

    def of(self, frame: pd.DataFrame) -> np.ndarray:
        base = frame[list(self._method.features)].to_numpy(dtype=self._dtype)
        if not self._method.with_kinds:
            return base
        kinds = frame[list(KIND_DUMMIES)].to_numpy(dtype=self._dtype)
        crossed = (base[:, None, :] * kinds[:, :, None]).reshape(len(frame), -1)
        return np.hstack([base, crossed])

    def penalized(self) -> np.ndarray:
        size = len(self._method.features)
        if not self._method.with_kinds:
            return np.zeros(size, dtype=bool)
        return np.r_[np.zeros(size, dtype=bool), np.ones(size * len(KIND_DUMMIES), dtype=bool)]

    def names(self) -> list[str]:
        """列の名前（重みを書き出すときに使う）。例: ``log_own``・``log_own×kind_dirt``。"""
        names = list(self._method.features)
        if self._method.with_kinds:
            names += [f"{feature}×{kind}" for kind in KIND_DUMMIES for feature in self._method.features]
        return names
