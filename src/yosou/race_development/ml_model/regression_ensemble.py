"""2つの回帰のモデルの値を平均する。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from yosou.shared.ml_model import FeatureData

from .regression_model import RegressionModel


class RegressionEnsemble:
    """LightGBM と CatBoost の回帰の値を平均する（設計書 03 の 4）。"""

    def __init__(self, members: Sequence[RegressionModel]) -> None:
        self._members = tuple(members)

    @property
    def members(self) -> tuple[RegressionModel, ...]:
        return self._members

    def predict(self, data: FeatureData) -> np.ndarray:
        """1行ずつの値（長さは行数）。"""
        return np.mean([member.predict(data) for member in self._members], axis=0)
