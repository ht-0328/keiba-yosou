"""LightGBM で回帰の学習・予測をする。"""

from __future__ import annotations

from pathlib import Path
from typing import Self

import joblib
import numpy as np

from yosou.shared.dataset import TrainingData
from yosou.shared.ml_model import FeatureData
from yosou.shared.setting import HyperparameterSettings

from .lightgbm_regressor import LightGbmRegressor

#: 目的関数（二乗誤差）。設定ファイルでは変えられない（設計書 14）。
_OBJECTIVE = {"objective": "regression"}


class LightGbmRegressionModel:
    """④ 4コーナーの位置・⑤ 上がりの速さを、LightGBM の回帰で当てる（設計書 12 の 2）。``RegressionModel`` を守る。"""

    name = "LightGBM"
    file_name = "lightgbm_regression.joblib"

    def __init__(self, regressor: LightGbmRegressor) -> None:
        self._regressor = regressor

    @classmethod
    def from_settings(cls, settings: HyperparameterSettings) -> Self:
        return cls(LightGbmRegressor(settings.lightgbm, _OBJECTIVE))

    def fit(self, train: TrainingData, valid: TrainingData) -> Self:
        self._regressor.fit(train, valid)
        return self

    def predict(self, data: FeatureData) -> np.ndarray:
        return self._regressor.predict(data)

    @property
    def tree_count(self) -> int:
        return self._regressor.tree_count

    def save(self, path: Path) -> None:
        joblib.dump(self._regressor.state(), path)

    @classmethod
    def load(cls, path: Path, settings: HyperparameterSettings) -> Self:
        return cls(LightGbmRegressor.from_state(joblib.load(path), settings.lightgbm))
