"""2つの分位点回帰のモデルの値を平均する。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from yosou.shared.ml_model import FeatureData

from .quantile_model import QuantileModel


class QuantileEnsemble:
    """LightGBM と CatBoost の分位点の値を平均し、行ごとに小さい順に並べ直す（設計書 03 の 3）。

    並べ直すのは、平均したあとに 10% の値が 90% の値を超えないようにするためである。
    """

    def __init__(self, members: Sequence[QuantileModel]) -> None:
        self._members = tuple(members)

    @property
    def members(self) -> tuple[QuantileModel, ...]:
        return self._members

    def predict_quantiles(self, data: FeatureData) -> np.ndarray:
        """行数 × 3（10%・50%・90% の値）。"""
        stacked = np.stack([member.predict_quantiles(data) for member in self._members], axis=0)
        return np.sort(stacked.mean(axis=0), axis=1)
