"""1着と3着以内を予想するモデルの組（LightGBM を種を変えて数本と CatBoost の平均）。"""

from __future__ import annotations

from dataclasses import dataclass

import lightgbm as lgb
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier

from .final_columns import FEATURES, MARKET_SHARE, MAX_DISTANCE, MIN_DISTANCE, MIN_FIELD, RACE_ID, TOP3, VALUE, WIN

#: LightGBM の種（本数）。
SEEDS: tuple[int, ...] = (0, 1, 2, 3, 4)
ROUNDS = 400
PARAMS = {"objective": "binary", "learning_rate": 0.03, "num_leaves": 15, "min_child_samples": 60, "feature_fraction": 0.7,
          "bagging_fraction": 0.8, "bagging_freq": 1, "lambda_l2": 10.0, "verbose": -1}
CAT_PARAMS = {"iterations": 500, "learning_rate": 0.04, "depth": 5, "l2_leaf_reg": 10, "verbose": 0, "random_seed": 0, "thread_count": 8}
#: 学ぶ目的（表の列名）。
TARGETS: tuple[str, ...] = ("win", "top3")


@dataclass(frozen=True)
class FinalModels:
    """``boosters`` と ``cats`` は 目的（``win``・``top3``）→ モデル。予想は LightGBM の平均と CatBoost の平均。"""

    boosters: dict[str, tuple[lgb.Booster, ...]]
    cats: dict[str, CatBoostClassifier]

    @staticmethod
    def scope(table: pd.DataFrame) -> pd.DataFrame:
        """学ぶ・予想する条件の走（距離 1300〜1600m・9頭以上）。"""
        return table[table["distance_m"].between(MIN_DISTANCE, MAX_DISTANCE) & (table["field_size"] >= MIN_FIELD)]

    @classmethod
    def fit(cls, table: pd.DataFrame) -> FinalModels:
        """``table`` は ``FinalFeatures.build`` の表のうち、結果の出ている走。条件の走だけで学ぶ。"""
        rows = cls.scope(table)
        features = rows[list(FEATURES)].astype(float)
        boosters, cats = {}, {}
        for target in TARGETS:
            label = rows[target].astype(int)
            boosters[target] = tuple(lgb.train({**PARAMS, "seed": seed}, lgb.Dataset(features, label), ROUNDS) for seed in SEEDS)
            cats[target] = CatBoostClassifier(**CAT_PARAMS).fit(features, label)
        return cls(boosters, cats)

    def score(self, table: pd.DataFrame) -> pd.DataFrame:
        """``table`` に 1着の確率（レースの中で足して 1）・3着以内の確率・割安さ（1着の確率 ÷ オッズが示す確率）を足す。"""
        features = table[list(FEATURES)].astype(float)
        scored = table.copy()
        win = self._predict("win", features)
        scored[WIN] = win / pd.Series(win, index=table.index).groupby(table[RACE_ID]).transform("sum")
        scored[TOP3] = self._predict("top3", features)
        scored[VALUE] = scored[WIN] / scored[MARKET_SHARE]
        return scored

    def _predict(self, target: str, features: pd.DataFrame) -> np.ndarray:
        trees = np.mean([booster.predict(features) for booster in self.boosters[target]], axis=0)
        return (trees + self.cats[target].predict_proba(features)[:, 1]) / 2
