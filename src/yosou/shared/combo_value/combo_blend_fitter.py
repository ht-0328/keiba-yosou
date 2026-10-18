"""組の確率の4つの重みを、当たった組に合わせて推定する。"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .combo_blend_features import FEATURE_COLUMNS
from .combo_blend_weights import ComboBlendWeights

#: 当たったかの列（真偽）。
HIT = "hit"


class ComboBlendFitter:
    """``ComboBlendFeatures.build`` の表に当たったかの列（``hit``）を付けたものから、重みを推定する（条件付きロジットの最尤推定）。

    対数尤度 = Σ_当たった組 (重み · もと) − Σ_レース 当たった組の数 × log Σ_そのレースの組 exp(重み · もと)。
    当たった組の確率の対数の合計を最大にする重みを、勾配つきで探す。出発点は「その券種自身の市場だけ」（own 1・ほか 0）。
    当たった組の無いレース（不成立）は落とす。行はレースごとにまとまっていなくてよい（中で並べ替える）。
    """

    def fit(self, frame: pd.DataFrame) -> ComboBlendWeights:
        rows = frame.sort_values("race_id", kind="stable")
        hits_per_race = rows.groupby("race_id", sort=False)[HIT].transform("sum")
        rows = rows[hits_per_race > 0]
        features = rows[list(FEATURE_COLUMNS)].to_numpy(dtype=float)
        hit = rows[HIT].to_numpy(dtype=bool)
        race = rows["race_id"].to_numpy()
        starts = np.flatnonzero(np.r_[True, race[1:] != race[:-1]])
        result = minimize(self._loss, np.array([1.0, 0.0, 0.0, 0.0]), args=(features, hit, starts), jac=True, method="L-BFGS-B")
        return ComboBlendWeights(*map(float, result.x))

    def _loss(self, weights: np.ndarray, features: np.ndarray, hit: np.ndarray, starts: np.ndarray) -> tuple[float, np.ndarray]:
        """負の対数尤度と、その勾配。"""
        sizes = np.diff(np.r_[starts, len(features)])
        score = features @ weights
        top = np.maximum.reduceat(score, starts)
        exponent = np.exp(score - np.repeat(top, sizes))
        total = np.add.reduceat(exponent, starts)
        hits = np.add.reduceat(hit.astype(float), starts)
        likelihood = score[hit].sum() - (hits * (np.log(total) + top)).sum()
        share = exponent / np.repeat(total, sizes)
        expected = np.add.reduceat(features * share[:, None], starts)
        gradient = features[hit].sum(axis=0) - (hits[:, None] * expected).sum(axis=0)
        return -likelihood, -gradient
