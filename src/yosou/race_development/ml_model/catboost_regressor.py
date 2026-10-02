"""CatBoost の回帰で学習・予測する。"""

from __future__ import annotations

from pathlib import Path
from typing import Self

import catboost
import numpy as np

from yosou.shared.dataset import TrainingData
from yosou.shared.ml_model import CatBoostEncoder, FeatureData
from yosou.shared.setting import CatBoostSettings


class CatBoostRegressor:
    """``CatBoostRegressor`` を1つ持ち、カテゴリ特徴量を共通の ``CatBoostEncoder`` で変えて学習・予測する（設計書 13）。

    回帰（``RMSE``）と分位点回帰（``MultiQuantile``。1つのモデルで3つの分位点）の両方の中身になる。
    列名とカテゴリ特徴量の列名は、保存したモデルの中に残る。
    """

    def __init__(self, settings: CatBoostSettings, loss_function: str) -> None:
        self._settings = settings
        self._loss_function = loss_function
        self._encoder: CatBoostEncoder | None = None
        self._regressor: catboost.CatBoostRegressor | None = None

    def fit(self, train: TrainingData, valid: TrainingData) -> Self:
        """学習する。検証データの損失が、木を足しても良くならなくなったら止める（設計書 13 の 4）。"""
        encoder = CatBoostEncoder(train.features.columns, train.categorical_columns)
        regressor = catboost.CatBoostRegressor(
            loss_function=self._loss_function, verbose=0, allow_writing_files=False, **self._settings.params,
        )
        regressor.fit(self._pool(encoder, train), eval_set=self._pool(encoder, valid),
                      early_stopping_rounds=self._settings.early_stopping_rounds)
        self._encoder, self._regressor = encoder, regressor
        return self

    def predict(self, data: FeatureData) -> np.ndarray:
        """回帰は長さ = 行数、分位点回帰は 行数 × 分位点の数。"""
        encoder, regressor = self._trained()
        pool = catboost.Pool(encoder.transform(data.features), cat_features=list(encoder.categorical_columns))
        return np.asarray(regressor.predict(pool))

    @property
    def tree_count(self) -> int:
        _, regressor = self._trained()
        return int(regressor.tree_count_)

    def save(self, path: Path) -> None:
        _, regressor = self._trained()
        regressor.save_model(str(path))

    @classmethod
    def load(cls, path: Path, settings: CatBoostSettings, loss_function: str) -> Self:
        regressor = catboost.CatBoostRegressor()
        regressor.load_model(str(path))
        columns = list(regressor.feature_names_)
        model = cls(settings, loss_function)
        model._encoder = CatBoostEncoder(columns, [columns[index] for index in regressor.get_cat_feature_indices()])
        model._regressor = regressor
        return model

    def _pool(self, encoder: CatBoostEncoder, data: TrainingData) -> catboost.Pool:
        return catboost.Pool(encoder.transform(data.features), data.label.astype("float64"),
                             cat_features=list(encoder.categorical_columns))

    def _trained(self) -> tuple[CatBoostEncoder, catboost.CatBoostRegressor]:
        if self._encoder is None or self._regressor is None:
            raise RuntimeError("CatBoost の回帰のモデルがまだ学習していません（fit か load を先に呼んでください）")
        return self._encoder, self._regressor
