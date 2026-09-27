"""1着になる確率を学習し、レースの中で合計 1 にそろえる。"""

from __future__ import annotations

import catboost as cb
import lightgbm as lgb
import numpy as np
import pandas as pd

#: 早期終了まで待つ本数。
_PATIENCE = 100


class WinModel:
    """LightGBM（``use_catboost`` なら CatBoost も）で「1着か」を学習し、確率をレース内で合計 1 にそろえる。

    2つ使うときは、そろえる前の確率を平均する。木の本数は、検証の年（``valid``）で決める。
    """

    def __init__(self, target: str = "won", use_catboost: bool = False, learning_rate: float = 0.05,
                 num_leaves: int = 63, min_child_samples: int = 200) -> None:
        self._target = target
        self._use_catboost = use_catboost
        self._learning_rate = learning_rate
        self._num_leaves = num_leaves
        self._min_child_samples = min_child_samples
        self._models: list = []

    def fit(self, train: pd.DataFrame, valid: pd.DataFrame, features: list[str]) -> WinModel:
        light = lgb.LGBMClassifier(objective="binary", n_estimators=5000, learning_rate=self._learning_rate,
                                   num_leaves=self._num_leaves, min_child_samples=self._min_child_samples,
                                   subsample=0.8, subsample_freq=1, colsample_bytree=0.7, verbose=-1)
        light.fit(train[features], train[self._target], eval_set=[(valid[features], valid[self._target])],
                  callbacks=[lgb.early_stopping(_PATIENCE, verbose=False)])
        self._models = [light]
        if self._use_catboost:
            cat = cb.CatBoostClassifier(iterations=3000, learning_rate=self._learning_rate, depth=7,
                                        loss_function="Logloss", verbose=False, early_stopping_rounds=_PATIENCE)
            cat.fit(train[features], train[self._target], eval_set=(valid[features], valid[self._target]))
            self._models.append(cat)
        self._features = features
        return self

    def predict(self, table: pd.DataFrame) -> np.ndarray:
        """レース内でそろえた確率（``table`` は race_id の列を持つ）。

        1着は合計 1、3着以内（``target`` が placed）は合計を複勝の対象の数（``places`` の列。3 か 2）にそろえる。
        """
        raw = np.mean([model.predict_proba(table[self._features])[:, 1] for model in self._models], axis=0)
        total = pd.Series(raw).groupby(table["race_id"].to_numpy()).transform("sum").to_numpy()
        places = table["places"].to_numpy() if self._target == "placed" else 1.0
        return np.clip(raw / total * places, 0.0, 1.0)

    def importance(self) -> pd.Series:
        light = self._models[0]
        return pd.Series(light.booster_.feature_importance("gain"), index=self._features).sort_values(ascending=False)
