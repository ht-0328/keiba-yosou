"""レースの中の着順の並びを学ぶ（LightGBM の lambdarank）。出発点はオッズから見た勝率の対数。"""

from __future__ import annotations

from typing import Self

import lightgbm
import numpy as np
import pandas as pd

from yosou.shared.dataset import RACE_ID, TrainingData
from yosou.shared.ml_model.lightgbm_encoder import LightGbmEncoder
from yosou.shared.setting import LightGbmSettings

#: 着順 → 並びの重さ（1着 3、2着 2、3着 1、ほか 0）。
_RELEVANCE = {1: 3, 2: 2, 3: 1}
#: 評価用の列の名前。
FINISH, MARKET_WIN = "確定着順", "オッズから見た勝率"
_FLOOR = 1e-4


class RankModel:
    """同じレースの馬を1つの組にして、着順の並び（1着 3・2着 2・3着 1・ほか 0）を lambdarank で学ぶ。

    出発点（``init_score``）は確定オッズから見た勝率の対数で、モデルは「市場の並びをどう入れ替えるか」だけを学ぶ。
    木を足すのは、検証データの 3着までの並びの当たり具合（NDCG@3）が良くならなくなるまで。
    ``score`` は出発点を足した点数（レースの中で比べる値。確率にするのは ``PlackettLuce``）。
    """

    def __init__(self, settings: LightGbmSettings) -> None:
        self._settings = settings
        self._encoder: LightGbmEncoder | None = None
        self._ranker: lightgbm.LGBMRanker | None = None

    def fit(self, train: TrainingData, valid: TrainingData) -> Self:
        train, valid = _by_race(train), _by_race(valid)
        encoder = LightGbmEncoder(self._settings.min_category_count).fit(train.features, train.categorical_columns)
        ranker = lightgbm.LGBMRanker(objective="lambdarank", verbose=-1, **self._settings.params)
        ranker.fit(
            encoder.transform(train.features), _relevance(train), group=_sizes(train), init_score=_start(train),
            eval_set=[(encoder.transform(valid.features), _relevance(valid))], eval_group=[_sizes(valid)],
            eval_init_score=[_start(valid)], eval_at=[3],
            callbacks=[lightgbm.early_stopping(self._settings.early_stopping_rounds, first_metric_only=True, verbose=False)],
        )
        self._encoder, self._ranker = encoder, ranker
        return self

    def score(self, data: TrainingData) -> np.ndarray:
        """``data`` の行の並びのままの点数（出発点を足したもの）。"""
        if self._encoder is None or self._ranker is None:
            raise RuntimeError("fit を先に呼んでください")
        return self._ranker.predict(self._encoder.transform(data.features), raw_score=True) + _start(data)

    @property
    def tree_count(self) -> int:
        if self._ranker is None:
            raise RuntimeError("fit を先に呼んでください")
        return int(self._ranker.best_iteration_ or self._ranker.n_estimators_)


def _by_race(data: TrainingData) -> TrainingData:
    """同じレースの行を続けて並べる（lambdarank は組の行が続いている必要がある）。"""
    index = data.ids[RACE_ID].astype(str).sort_values(kind="stable").index
    return TrainingData(data.ids.loc[index], data.features.loc[index], data.targets.loc[index], data.evaluation.loc[index],
                        data.catalog, data.label_name, data.class_labels)


def _sizes(data: TrainingData) -> np.ndarray:
    races = data.ids[RACE_ID].astype(str).to_numpy()
    _, starts, counts = np.unique(races, return_index=True, return_counts=True)
    return counts[np.argsort(starts)]


def _relevance(data: TrainingData) -> np.ndarray:
    finish = pd.to_numeric(data.evaluation[FINISH], errors="coerce")
    return finish.map(_RELEVANCE).fillna(0).astype(int).to_numpy()


def _start(data: TrainingData) -> np.ndarray:
    return np.log(np.clip(pd.to_numeric(data.evaluation[MARKET_WIN], errors="coerce").fillna(_FLOOR).to_numpy(dtype=float), _FLOOR, 1.0))
