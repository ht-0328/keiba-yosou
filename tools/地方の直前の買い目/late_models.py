"""買う馬らしさ（分類）と単勝の戻りの見込み（回帰）の2つのモデル。種を変えた数本の平均で当てる。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import lightgbm as lgb
import numpy as np
import pandas as pd

from .late_columns import LIKENESS, PAYBACK
from .late_features import LateFeatures
from .late_targets import RETURN, TEACHER_BUYS

#: 種（この本数の平均で当てる。作るたびの振れを減らす）。
SEEDS: tuple[int, ...] = (100, 101, 102)
#: 買う馬らしさのモデル（細かく分ける）と、戻りの見込みのモデル（当たり外れの振れが大きいので、浅く・葉を大きく）の設定。
LIKENESS_PARAMS: dict[str, object] = dict(objective="binary", learning_rate=0.03, num_leaves=31, min_child_samples=100, subsample=0.8,
                                          subsample_freq=1, colsample_bytree=0.8, reg_lambda=5.0, verbose=-1)
PAYBACK_PARAMS: dict[str, object] = dict(objective="regression", learning_rate=0.03, num_leaves=7, min_child_samples=500, subsample=0.8,
                                         subsample_freq=1, colsample_bytree=0.8, reg_lambda=10.0, verbose=-1)
#: 木の本数。
LIKENESS_ROUNDS = 400
PAYBACK_ROUNDS = 300


@dataclass(frozen=True)
class LateModels:
    """``likeness``・``payback`` は種ごとの LightGBM の Booster。``score`` は特徴量の表に ``LIKENESS``・``PAYBACK`` の列を足す。"""

    likeness: tuple[lgb.Booster, ...]
    payback: tuple[lgb.Booster, ...]

    @classmethod
    def fit(cls, rows: pd.DataFrame, seeds: Sequence[int] = SEEDS) -> LateModels:
        """``rows`` は特徴量と答えの列（``LateTargets``）のある表。買う馬らしさは先生の確率のある行だけで学ぶ。"""
        taught = rows[rows[TEACHER_BUYS].notna()]
        likeness = tuple(cls._train(LIKENESS_PARAMS, LIKENESS_ROUNDS, taught, taught[TEACHER_BUYS], seed) for seed in seeds)
        payback = tuple(cls._train(PAYBACK_PARAMS, PAYBACK_ROUNDS, rows, rows[RETURN], seed) for seed in seeds)
        return cls(likeness, payback)

    def score(self, features: pd.DataFrame) -> pd.DataFrame:
        matrix = LateFeatures.matrix(features)
        scored = features.copy()
        scored[LIKENESS] = np.mean([booster.predict(matrix) for booster in self.likeness], axis=0)
        scored[PAYBACK] = np.mean([booster.predict(matrix) for booster in self.payback], axis=0)
        return scored

    @staticmethod
    def _train(params: dict[str, object], rounds: int, rows: pd.DataFrame, target: pd.Series, seed: int) -> lgb.Booster:
        data = lgb.Dataset(LateFeatures.matrix(rows), label=target.astype(float))
        return lgb.train({**params, "seed": seed}, data, num_boost_round=rounds)
