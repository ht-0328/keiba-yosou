"""Platt scaling で確率をそろえ直す。"""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression

#: 確率をロジットにするときの端の丸め。
_EDGE = 1e-4
#: 正則化をほぼ効かせない強さ（係数2つだけなので、縮める必要が無い）。
_NO_PENALTY = 1e6


class PlattCalibration:
    """Platt scaling（確率のロジットに、ロジスティック回帰で傾きと切片を当てる）で確率をそろえ直す。

    較正後の確率 = 1 ÷ (1 + exp(−(a × logit(確率) + b)))。a = 1・b = 0 なら何も変えない。
    例: a = 0.9・b = −0.1 なら、全体を少し下げ、高い確率ほど強く縮める。形が決まっているので、少ないデータでも振れにくい。
    """

    def __init__(self) -> None:
        self._regression: LogisticRegression | None = None

    def fit(self, probability: np.ndarray, label: np.ndarray) -> PlattCalibration:
        self._regression = LogisticRegression(C=_NO_PENALTY).fit(self._logit(probability), label)
        return self

    def apply(self, probability: np.ndarray) -> np.ndarray:
        if self._regression is None:
            raise RuntimeError("まだ学んでいません（fit を先に呼んでください）")
        return self._regression.predict_proba(self._logit(probability))[:, 1]

    def _logit(self, probability: np.ndarray) -> np.ndarray:
        clipped = np.clip(np.asarray(probability, dtype="float64"), _EDGE, 1.0 - _EDGE)
        return np.log(clipped / (1.0 - clipped)).reshape(-1, 1)
