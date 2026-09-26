"""LightGBM で分位点回帰の学習・予測をする。"""

from __future__ import annotations

from pathlib import Path
from typing import Self

import joblib
import numpy as np

from yosou.shared.dataset import TrainingData
from yosou.shared.ml_model import FeatureData
from yosou.shared.setting import HyperparameterSettings

from .lightgbm_regressor import LightGbmRegressor

#: 当てる分位点（10%・50%・90%。設計書 10 の 4）。
QUANTILES: tuple[float, float, float] = (0.1, 0.5, 0.9)


class LightGbmQuantileModel:
    """③ 前半タイム・⑥ 後半タイムの基準との差を、分位点ごとに1つの ``LGBMRegressor``（3つ）で当てる（設計書 12 の 2）。

    ``QuantileModel`` を守る。LightGBM は1つのモデルで1つの分位点しか学べないため、3つ持つ。
    """

    name = "LightGBM"
    file_name = "lightgbm_quantile.joblib"

    def __init__(self, regressors: list[LightGbmRegressor]) -> None:
        self._regressors = regressors

    @classmethod
    def from_settings(cls, settings: HyperparameterSettings) -> Self:
        return cls([LightGbmRegressor(settings.lightgbm, {"objective": "quantile", "alpha": alpha}) for alpha in QUANTILES])

    def fit(self, train: TrainingData, valid: TrainingData) -> Self:
        for regressor in self._regressors:
            regressor.fit(train, valid)
        return self

    def predict_quantiles(self, data: FeatureData) -> np.ndarray:
        """行数 × 3（10%・50%・90% の値）。"""
        return np.column_stack([regressor.predict(data) for regressor in self._regressors])

    @property
    def tree_count(self) -> int:
        """真ん中の値（50%）のモデルの木の数。"""
        return self._regressors[1].tree_count

    def save(self, path: Path) -> None:
        joblib.dump([regressor.state() for regressor in self._regressors], path)

    @classmethod
    def load(cls, path: Path, settings: HyperparameterSettings) -> Self:
        return cls([LightGbmRegressor.from_state(state, settings.lightgbm) for state in joblib.load(path)])
