"""LightGBM の並べ替え（lambdarank）で、人気薄が勝ったレースの「人気薄のうちどれが勝ったか」を学ぶ。"""

from __future__ import annotations

import lightgbm
import numpy as np

from yosou.shared.ml_model.lightgbm_encoder import LightGbmEncoder
from yosou.shared.setting import LightGbmSettings

from .longshot_data import LongshotData

_QUIET = -1


class RankLightGbm:
    """レースを1つの組にして並べ替えを学ぶ。出発点はオッズから見た勝率のロジット（``init_score``）。``raw`` は出発点からの上げ下げ。
    行はレースごとにまとまって並んでいること（``LongshotData`` は学習の表の並びのまま＝レースごと）。"""

    name = "LightGBM"

    def __init__(self, settings: LightGbmSettings, threads: int) -> None:
        self._settings = settings
        self._threads = threads
        self._encoder: LightGbmEncoder | None = None
        self._model: lightgbm.LGBMRanker | None = None

    def fit(self, train: LongshotData, valid: LongshotData, train_weight: np.ndarray, valid_weight: np.ndarray) -> RankLightGbm:
        encoder = LightGbmEncoder(self._settings.min_category_count).fit(train.features, train.categorical)
        model = lightgbm.LGBMRanker(objective="lambdarank", verbose=_QUIET, n_jobs=self._threads, eval_at=[1, 3],
                                    **self._settings.params)
        model.fit(
            encoder.transform(train.features), train.label, group=self._groups(train), init_score=train.baseline.to_numpy(),
            eval_set=[(encoder.transform(valid.features), valid.label)], eval_group=[self._groups(valid)],
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

    @staticmethod
    def _groups(data: LongshotData) -> np.ndarray:
        """レースごとの行の数（並びの順）。"""
        race = data.race_ids.to_numpy()
        starts = np.r_[True, race[1:] != race[:-1]]
        return np.diff(np.r_[np.flatnonzero(starts), len(race)])
