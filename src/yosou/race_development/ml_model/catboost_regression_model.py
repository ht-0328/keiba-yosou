"""CatBoost で回帰の学習・予測をする。"""

from __future__ import annotations

from pathlib import Path
from typing import Self

import numpy as np

from yosou.shared.dataset import TrainingData
from yosou.shared.ml_model import FeatureData
from yosou.shared.setting import HyperparameterSettings

from .catboost_regressor import CatBoostRegressor

#: 目的関数（二乗誤差）。設定ファイルでは変えられない（設計書 14）。
_LOSS = "RMSE"


class CatBoostRegressionModel:
    """④ 4コーナーの位置・⑤ 上がりの速さを、CatBoost の回帰で当てる（設計書 13 の 2）。``RegressionModel`` を守る。"""

    name = "CatBoost"
    file_name = "catboost_regression.cbm"

    def __init__(self, regressor: CatBoostRegressor) -> None:
        self._regressor = regressor

    @classmethod
    def from_settings(cls, settings: HyperparameterSettings) -> Self:
        return cls(CatBoostRegressor(settings.catboost, _LOSS))

    def fit(self, train: TrainingData, valid: TrainingData) -> Self:
        self._regressor.fit(train, valid)
        return self

    def predict(self, data: FeatureData) -> np.ndarray:
        return self._regressor.predict(data)

    @property
    def tree_count(self) -> int:
        return self._regressor.tree_count

    def save(self, path: Path) -> None:
        self._regressor.save(path)

    @classmethod
    def load(cls, path: Path, settings: HyperparameterSettings) -> Self:
        return cls(CatBoostRegressor.load(path, settings.catboost, _LOSS))
