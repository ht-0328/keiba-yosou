"""CatBoost で、重みつき・基準つきの二値分類を学ぶ（人気薄の1着）。"""

from __future__ import annotations

import catboost
import numpy as np

from yosou.shared.ml_model.catboost_encoder import CatBoostEncoder
from yosou.shared.setting import CatBoostSettings

from .longshot_data import LongshotData


class WeightedCatBoost:
    """``fit`` で学び、``raw`` で基準からの上げ下げ（ロジット）を返す。基準は ``Pool`` の ``baseline`` で渡す。
    カテゴリ特徴量の扱いは今のモデルと同じ（``CatBoostEncoder``）。"""

    name = "CatBoost"

    def __init__(self, settings: CatBoostSettings, threads: int) -> None:
        self._settings = settings
        self._threads = threads
        self._encoder: CatBoostEncoder | None = None
        self._model: catboost.CatBoostClassifier | None = None

    def fit(self, train: LongshotData, valid: LongshotData, train_weight: np.ndarray, valid_weight: np.ndarray) -> WeightedCatBoost:
        encoder = CatBoostEncoder(train.features.columns, train.categorical)
        model = catboost.CatBoostClassifier(loss_function="Logloss", verbose=0, allow_writing_files=False,
                                            thread_count=self._threads, **self._settings.params)
        model.fit(self._pool(encoder, train, train_weight), eval_set=self._pool(encoder, valid, valid_weight),
                  early_stopping_rounds=self._settings.early_stopping_rounds)
        self._encoder, self._model = encoder, model
        return self

    def raw(self, data: LongshotData) -> np.ndarray:
        if self._encoder is None or self._model is None:
            raise RuntimeError("CatBoost のモデルがまだ学習していません")
        pool = catboost.Pool(self._encoder.transform(data.features), cat_features=list(self._encoder.categorical_columns))
        return self._model.predict(pool, prediction_type="RawFormulaVal")

    @property
    def tree_count(self) -> int:
        return int(self._model.tree_count_) if self._model is not None else 0

    @staticmethod
    def _pool(encoder: CatBoostEncoder, data: LongshotData, weight: np.ndarray) -> catboost.Pool:
        return catboost.Pool(encoder.transform(data.features), data.label, cat_features=list(encoder.categorical_columns),
                             baseline=data.baseline.to_numpy(), weight=weight)
