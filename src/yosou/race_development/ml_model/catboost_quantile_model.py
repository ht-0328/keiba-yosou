"""CatBoost で分位点回帰の学習・予測をする。"""

from __future__ import annotations

from pathlib import Path
from typing import Self

import numpy as np

from yosou.shared.dataset import TrainingData
from yosou.shared.ml_model import FeatureData
from yosou.shared.setting import HyperparameterSettings

from .catboost_regressor import CatBoostRegressor
from .lightgbm_quantile_model import QUANTILES

#: 目的関数（1つのモデルで 10%・50%・90%）。設定ファイルでは変えられない（設計書 14）。
_LOSS = "MultiQuantile:alpha=" + ",".join(str(alpha) for alpha in QUANTILES)


class CatBoostQuantileModel:
    """③ 前半タイム・⑥ 後半タイムの基準との差を、1つの ``CatBoostRegressor``（``MultiQuantile``）で当てる（設計書 13 の 2）。

    ``QuantileModel`` を守る。
    """

    name = "CatBoost"
    file_name = "catboost_quantile.cbm"

    def __init__(self, regressor: CatBoostRegressor) -> None:
        self._regressor = regressor

    @classmethod
    def from_settings(cls, settings: HyperparameterSettings) -> Self:
        return cls(CatBoostRegressor(settings.catboost, _LOSS))

    def fit(self, train: TrainingData, valid: TrainingData) -> Self:
        self._regressor.fit(train, valid)
        return self

    def predict_quantiles(self, data: FeatureData) -> np.ndarray:
        """行数 × 3（10%・50%・90% の値）。"""
        return self._regressor.predict(data).reshape(len(data), len(QUANTILES))

    @property
    def tree_count(self) -> int:
        return self._regressor.tree_count

    def save(self, path: Path) -> None:
        self._regressor.save(path)

    @classmethod
    def load(cls, path: Path, settings: HyperparameterSettings) -> Self:
        return cls(CatBoostRegressor.load(path, settings.catboost, _LOSS))
