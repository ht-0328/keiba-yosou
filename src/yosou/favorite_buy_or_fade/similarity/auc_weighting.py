"""列ごとの重みを、馬券外との関係の強さで決める。"""

from __future__ import annotations

import numpy as np
from scipy.stats import rankdata


class AucWeighting:
    """列ごとの重みを、その列と「馬券外か」との関係の強さで決める（設計書 12 の 4。方針の ``column_weighting`` の ``method = "馬券外とのAUC"``）。

    単位の学習データで、列ごとに「馬券外か」との AUC（その列の値が大きい馬ほど馬券外になっているか。0.5 なら関係なし、
    1 か 0 なら完全に分けられる）を出し、|2 × AUC − 1|（0〜1）を重みにする。馬券外と関係の弱い列が、距離に効かなくなる。
    ``keep`` が 1 以上なら、関係の強い順にその列数だけを重み 1 で使い、ほかの列は 0（使わない）にする。
    AUC は値の順位だけで決まるので、標準化や、まとまりの重みを掛ける前後で変わらない。
    """

    def __init__(self, keep: int = 0) -> None:
        self._keep = keep
        self._weights = np.empty(0)

    def fit(self, matrix: np.ndarray, is_out: np.ndarray | None) -> AucWeighting:
        """``matrix`` は単位の1番人気全員の行列、``is_out`` は行ごとに馬券外か。"""
        if is_out is None:
            raise ValueError("列ごとの重みを馬券外との AUC で決めるには、行ごとに馬券外かの列が要ります")
        members = np.asarray(is_out, dtype=bool)
        positives, negatives = int(members.sum()), int((~members).sum())
        if positives == 0 or negatives == 0:
            raise ValueError("列ごとの重みを決めるには、馬券外の馬と馬券内の馬の両方が要ります")
        ranks = rankdata(matrix, axis=0)
        auc = (ranks[members].sum(axis=0) - positives * (positives + 1) / 2) / (positives * negatives)
        strength = np.abs(2 * auc - 1)
        self._weights = strength if self._keep <= 0 else self._top(strength)
        return self

    @property
    def weights(self) -> np.ndarray:
        """列ごとの重み（行列の列と同じ並び）。"""
        return self._weights

    def _top(self, strength: np.ndarray) -> np.ndarray:
        """関係の強い順に ``keep`` 列だけ 1、ほかは 0。"""
        weights = np.zeros_like(strength)
        weights[np.argsort(-strength, kind="stable")[:self._keep]] = 1.0
        return weights
