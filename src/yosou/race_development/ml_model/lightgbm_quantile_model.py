"""LightGBM で分位点回帰の学習・予測をする。"""

from __future__ import annotations

from pathlib import Path
from typing import Self

import joblib
import numpy as np

from yosou.shared.dataset import TrainingData
from yosou.shared.ml_model import FeatureData
from yosou.shared.setting import HyperparameterSettings

from .interval_width import IntervalWidth
from .interval_width_fitter import IntervalWidthFitter
from .lightgbm_regressor import LightGbmRegressor
from .validation_halves import ValidationHalves

#: 当てる分位点（10%・50%・90%。設計書 10 の 4）。
QUANTILES: tuple[float, float, float] = (0.1, 0.5, 0.9)


class LightGbmQuantileModel:
    """③ 前半タイム・⑥ 後半タイムの基準との差を、分位点ごとに1つの ``LGBMRegressor``（3つ）で当てる（設計書 12 の 2）。

    ``QuantileModel`` を守る。LightGBM は1つのモデルで1つの分位点しか学べないため、3つ持つ。
    ``fit`` では、検証データを前半と後半に分け、前半で早期終了しながら学習し、後半で 80% の幅の倍率を決める
    （``IntervalWidthFitter``。① 先頭の温度と同じ分け方）。``predict_quantiles`` は倍率を掛けた値を返す。
    """

    name = "LightGBM"
    file_name = "lightgbm_quantile.joblib"

    def __init__(self, regressors: list[LightGbmRegressor], width: IntervalWidth | None = None) -> None:
        self._regressors = regressors
        self._width = width or IntervalWidth()

    @classmethod
    def from_settings(cls, settings: HyperparameterSettings) -> Self:
        return cls([LightGbmRegressor(settings.lightgbm, {"objective": "quantile", "alpha": alpha}) for alpha in QUANTILES])

    @property
    def width(self) -> IntervalWidth:
        return self._width

    def fit(self, train: TrainingData, valid: TrainingData) -> Self:
        first_half, second_half = ValidationHalves().split(valid)
        for regressor in self._regressors:
            regressor.fit(train, first_half)
        self._width = IntervalWidthFitter().fit(self._raw(second_half), second_half.label.to_numpy())
        return self

    def predict_quantiles(self, data: FeatureData) -> np.ndarray:
        """行数 × 3（10%・50%・90% の値。幅の倍率を掛けたもの）。"""
        return self._width.apply(self._raw(data))

    @property
    def tree_count(self) -> int:
        """真ん中の値（50%）のモデルの木の数。"""
        return self._regressors[1].tree_count

    def save(self, path: Path) -> None:
        joblib.dump([regressor.state() for regressor in self._regressors], path)
        self._width.save(path)

    @classmethod
    def load(cls, path: Path, settings: HyperparameterSettings) -> Self:
        regressors = [LightGbmRegressor.from_state(state, settings.lightgbm) for state in joblib.load(path)]
        return cls(regressors, IntervalWidth.load(path))

    def _raw(self, data: FeatureData) -> np.ndarray:
        """倍率を掛ける前の、3つのモデルの値。"""
        return np.column_stack([regressor.predict(data) for regressor in self._regressors])
