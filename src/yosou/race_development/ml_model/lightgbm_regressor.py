"""LightGBM の回帰（1つの目的関数）で学習・予測する。"""

from __future__ import annotations

from typing import Any, Self

import lightgbm
import numpy as np

from yosou.shared.dataset import TrainingData
from yosou.shared.ml_model import FeatureData, LightGbmEncoder
from yosou.shared.setting import LightGbmSettings

#: 学習の途中経過を出さない。
_QUIET = -1


class LightGbmRegressor:
    """``LGBMRegressor`` を1つ持ち、カテゴリ特徴量を共通の ``LightGbmEncoder`` で変えて学習・予測する（設計書 12）。

    回帰（``objective="regression"``）と分位点回帰（``objective="quantile"``、``alpha`` 付き）の両方の中身になる。
    保存は、素の辞書（エンコーダーの中身と学習済みの ``LGBMRegressor``）で行う（``state``・``from_state``）。
    """

    def __init__(self, settings: LightGbmSettings, objective_params: dict[str, Any]) -> None:
        self._settings = settings
        self._objective_params = dict(objective_params)
        self._encoder: LightGbmEncoder | None = None
        self._regressor: lightgbm.LGBMRegressor | None = None

    def fit(self, train: TrainingData, valid: TrainingData) -> Self:
        """学習する。検証データの損失が、木を足しても良くならなくなったら止める（設計書 12 の 4）。"""
        encoder = LightGbmEncoder(self._settings.min_category_count).fit(train.features, train.categorical_columns)
        regressor = lightgbm.LGBMRegressor(verbose=_QUIET, **self._settings.params, **self._objective_params)
        early_stopping = lightgbm.early_stopping(self._settings.early_stopping_rounds, verbose=False)
        regressor.fit(
            encoder.transform(train.features), train.label.astype("float64"),
            eval_X=encoder.transform(valid.features), eval_y=valid.label.astype("float64"), callbacks=[early_stopping],
        )
        self._encoder, self._regressor = encoder, regressor
        return self

    def predict(self, data: FeatureData) -> np.ndarray:
        encoder, regressor = self._trained()
        return regressor.predict(encoder.transform(data.features))

    @property
    def tree_count(self) -> int:
        _, regressor = self._trained()
        return int(regressor.best_iteration_ or regressor.n_estimators_)

    def state(self) -> dict[str, Any]:
        """保存するときの形（素の辞書）。"""
        encoder, regressor = self._trained()
        return {"encoder": encoder.state(), "regressor": regressor, "objective_params": self._objective_params}

    @classmethod
    def from_state(cls, state: dict[str, Any], settings: LightGbmSettings) -> Self:
        model = cls(settings, state["objective_params"])
        model._encoder = LightGbmEncoder.from_state(state["encoder"])
        model._regressor = state["regressor"]
        return model

    def _trained(self) -> tuple[LightGbmEncoder, lightgbm.LGBMRegressor]:
        if self._encoder is None or self._regressor is None:
            raise RuntimeError("LightGBM の回帰のモデルがまだ学習していません（fit か load を先に呼んでください）")
        return self._encoder, self._regressor
