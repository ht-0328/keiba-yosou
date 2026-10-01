"""CatBoost で分位点回帰の学習・予測をする。"""

from __future__ import annotations

from pathlib import Path
from typing import Self

import numpy as np

from yosou.shared.dataset import TrainingData
from yosou.shared.ml_model import FeatureData
from yosou.shared.setting import HyperparameterSettings

from .catboost_regressor import CatBoostRegressor
from .interval_width import IntervalWidth
from .interval_width_fitter import IntervalWidthFitter
from .lightgbm_quantile_model import QUANTILES
from .validation_halves import ValidationHalves

#: 目的関数（1つのモデルで 10%・50%・90%）。設定ファイルでは変えられない（設計書 14）。
_LOSS = "MultiQuantile:alpha=" + ",".join(str(alpha) for alpha in QUANTILES)


class CatBoostQuantileModel:
    """③ 前半タイム・⑥ 後半タイムの基準との差を、1つの ``CatBoostRegressor``（``MultiQuantile``）で当てる（設計書 13 の 2）。

    ``QuantileModel`` を守る。``fit`` では、検証データの前半で早期終了し、後半で 80% の幅の倍率を決める
    （``LightGbmQuantileModel`` と同じ）。
    """

    name = "CatBoost"
    file_name = "catboost_quantile.cbm"

    def __init__(self, regressor: CatBoostRegressor, width: IntervalWidth | None = None) -> None:
        self._regressor = regressor
        self._width = width or IntervalWidth()

    @classmethod
    def from_settings(cls, settings: HyperparameterSettings) -> Self:
        return cls(CatBoostRegressor(settings.catboost, _LOSS))

    @property
    def width(self) -> IntervalWidth:
        return self._width

    def fit(self, train: TrainingData, valid: TrainingData) -> Self:
        first_half, second_half = ValidationHalves().split(valid)
        self._regressor.fit(train, first_half)
        self._width = IntervalWidthFitter().fit(self._raw(second_half), second_half.label.to_numpy())
        return self

    def predict_quantiles(self, data: FeatureData) -> np.ndarray:
        """行数 × 3（10%・50%・90% の値。幅の倍率を掛けたもの）。"""
        return self._width.apply(self._raw(data))

    @property
    def tree_count(self) -> int:
        return self._regressor.tree_count

    def save(self, path: Path) -> None:
        self._regressor.save(path)
        self._width.save(path)

    @classmethod
    def load(cls, path: Path, settings: HyperparameterSettings) -> Self:
        return cls(CatBoostRegressor.load(path, settings.catboost, _LOSS), IntervalWidth.load(path))

    def _raw(self, data: FeatureData) -> np.ndarray:
        """倍率を掛ける前の値（行数 × 3）。"""
        return self._regressor.predict(data).reshape(len(data), len(QUANTILES))
