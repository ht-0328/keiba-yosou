"""CatBoost の並べ替え（YetiRank）で、人気薄が勝ったレースの「人気薄のうちどれが勝ったか」を学ぶ。"""

from __future__ import annotations

import catboost
import numpy as np

from yosou.shared.ml_model.catboost_encoder import CatBoostEncoder
from yosou.shared.setting import CatBoostSettings

from .longshot_data import LongshotData


class RankCatBoost:
    """レースを1つの組（``group_id``）にして並べ替えを学ぶ。出発点はオッズから見た勝率のロジット（``baseline``）。``raw`` は出発点からの上げ下げ。"""

    name = "CatBoost"

    def __init__(self, settings: CatBoostSettings, threads: int) -> None:
        self._settings = settings
        self._threads = threads
        self._encoder: CatBoostEncoder | None = None
        self._model: catboost.CatBoost | None = None

    def fit(self, train: LongshotData, valid: LongshotData, train_weight: np.ndarray, valid_weight: np.ndarray) -> RankCatBoost:
        encoder = CatBoostEncoder(train.features.columns, train.categorical)
        params = {**self._settings.params, "loss_function": "YetiRank", "verbose": 0, "allow_writing_files": False,
                  "thread_count": self._threads}
        model = catboost.CatBoost(params)
        model.fit(self._pool(encoder, train), eval_set=self._pool(encoder, valid), early_stopping_rounds=self._settings.early_stopping_rounds)
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
    def _pool(encoder: CatBoostEncoder, data: LongshotData) -> catboost.Pool:
        return catboost.Pool(encoder.transform(data.features), data.label, cat_features=list(encoder.categorical_columns),
                             baseline=data.baseline.to_numpy(), group_id=data.race_ids.to_numpy())
