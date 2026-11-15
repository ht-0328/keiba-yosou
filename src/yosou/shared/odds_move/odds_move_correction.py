"""オッズの動きで、当日の予想の確率を直す。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .odds_move_features import OddsMoveFeatures
from .odds_move_fitter import logit
from .odds_move_weights import OddsMoveWeights

#: 目的の名前（重みのファイルの鍵）。
TARGET_TOP3, TARGET_WIN = "3着以内", "1着"


class OddsMoveCorrection:
    """3着以内と1着の重み（``weights``。目的の名前 → 重み）で、1レースの全頭の確率を直す。

    直した確率 = 1 ÷（1 ＋ exp(−(今の確率のロジット ＋ 切片 ＋ 材料 · 重み)))。1着の確率は、直したあとにレースの中で合計 1 にそろえる。
    重みの無い目的は直さない。
    """

    def __init__(self, weights: dict[str, OddsMoveWeights]) -> None:
        self._weights = dict(weights)
        self._features = OddsMoveFeatures()

    def top3(self, probability: pd.Series, win_odds: pd.Series, eve_odds: pd.Series) -> pd.Series:
        return self._corrected(TARGET_TOP3, probability, win_odds, eve_odds)

    def win(self, probability: pd.Series, win_odds: pd.Series, eve_odds: pd.Series) -> pd.Series:
        corrected = self._corrected(TARGET_WIN, probability, win_odds, eve_odds)
        if TARGET_WIN not in self._weights or corrected.sum() <= 0:
            return corrected
        return corrected / corrected.sum()

    def _corrected(self, target: str, probability: pd.Series, win_odds: pd.Series, eve_odds: pd.Series) -> pd.Series:
        weights = self._weights.get(target)
        if weights is None:
            return probability
        x = self._features.matrix(win_odds, eve_odds)
        raw = logit(probability.to_numpy(dtype=float)) + weights.intercept + x @ weights.slopes()
        return pd.Series(1.0 / (1.0 + np.exp(-raw)), index=probability.index, name=probability.name)
