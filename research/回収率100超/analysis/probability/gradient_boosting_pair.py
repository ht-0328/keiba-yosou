"""LightGBM と CatBoost の2つで学習して、確率を平均する。"""

from __future__ import annotations

import catboost as cb
import lightgbm as lgb
import numpy as np
import pandas as pd

#: 早期終了まで待つ本数。検証データの当たり具合がこの本数だけ良くならなければ止める。
_PATIENCE = 150


class GradientBoostingPair:
    """LightGBM と CatBoost を同じ特徴量で学習し、出た確率を平均する。

    2つのライブラリは木の作り方が違う（LightGBM は葉を1つずつ増やし、CatBoost は深さをそろえて増やす）ので、
    当てそこなう場所がずれる。平均すると、片方の外しがもう片方で埋まる。
    期待値で買う以上、確率がそのまま買うかどうかを決めるので、この安定は効く。

    木の本数は、直前の1年（``valid``）で決める。学習には使わない年である。
    """

    def __init__(self, learning_rate: float = 0.03, max_trees: int = 4000) -> None:
        self._learning_rate = learning_rate
        self._max_trees = max_trees
        self._light: lgb.LGBMClassifier | None = None
        self._cat: cb.CatBoostClassifier | None = None

    def fit(self, features: pd.DataFrame, target: np.ndarray,
            valid_features: pd.DataFrame, valid_target: np.ndarray) -> GradientBoostingPair:
        self._light = lgb.LGBMClassifier(
            objective="binary", n_estimators=self._max_trees, learning_rate=self._learning_rate,
            num_leaves=63, min_child_samples=200, subsample=0.8, subsample_freq=1,
            colsample_bytree=0.8, verbose=-1)
        self._light.fit(features, target, eval_X=valid_features, eval_y=valid_target,
                        callbacks=[lgb.early_stopping(_PATIENCE, verbose=False)])
        self._cat = cb.CatBoostClassifier(
            iterations=self._max_trees, learning_rate=self._learning_rate, depth=6,
            loss_function="Logloss", verbose=False, early_stopping_rounds=_PATIENCE)
        self._cat.fit(features, target, eval_set=(valid_features, valid_target))
        return self

    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """2つのモデルの確率の平均。"""
        return (self.predict_each(features).mean(axis=0))

    def predict_each(self, features: pd.DataFrame) -> np.ndarray:
        """モデルごとの確率（2行 × 行数）。1行目が LightGBM、2行目が CatBoost。"""
        if self._light is None or self._cat is None:
            raise RuntimeError("まだ学習していません（fit を先に呼んでください）")
        return np.stack([self._light.predict_proba(features)[:, 1],
                         self._cat.predict_proba(features)[:, 1]])
