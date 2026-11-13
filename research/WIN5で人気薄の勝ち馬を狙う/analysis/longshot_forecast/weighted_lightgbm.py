"""LightGBM で、重みつき・基準つきの二値分類を学ぶ（人気薄の1着）。"""

from __future__ import annotations

import lightgbm
import numpy as np

from yosou.shared.ml_model.lightgbm_encoder import LightGbmEncoder
from yosou.shared.setting import LightGbmSettings

from .longshot_data import LongshotData

_QUIET = -1


class WeightedLightGbm:
    """``fit`` で学び、``raw`` で基準からの上げ下げ（ロジット）を返す。基準（オッズから見た勝率のロジット）は ``init_score`` で渡す。
    カテゴリ特徴量の扱いは今のモデルと同じ（``LightGbmEncoder``）。"""

    name = "LightGBM"

    def __init__(self, settings: LightGbmSettings, threads: int) -> None:
        self._settings = settings
        self._threads = threads
        self._encoder: LightGbmEncoder | None = None
        self._model: lightgbm.LGBMClassifier | None = None

    def fit(self, train: LongshotData, valid: LongshotData, train_weight: np.ndarray, valid_weight: np.ndarray) -> WeightedLightGbm:
        encoder = LightGbmEncoder(self._settings.min_category_count).fit(train.features, train.categorical)
        model = lightgbm.LGBMClassifier(objective="binary", verbose=_QUIET, n_jobs=self._threads, **self._settings.params)
        model.fit(
            encoder.transform(train.features), train.label, sample_weight=train_weight, init_score=train.baseline.to_numpy(),
            eval_set=[(encoder.transform(valid.features), valid.label)], eval_sample_weight=[valid_weight],
            eval_init_score=[valid.baseline.to_numpy()],
            callbacks=[lightgbm.early_stopping(self._settings.early_stopping_rounds, verbose=False)],
        )
        self._encoder, self._model = encoder, model
        return self

    def raw(self, data: LongshotData) -> np.ndarray:
        if self._encoder is None or self._model is None:
            raise RuntimeError("LightGBM のモデルがまだ学習していません")
        return self._model.predict(self._encoder.transform(data.features), raw_score=True)

    @property
    def tree_count(self) -> int:
        return int(self._model.best_iteration_ or self._model.n_estimators_) if self._model is not None else 0
