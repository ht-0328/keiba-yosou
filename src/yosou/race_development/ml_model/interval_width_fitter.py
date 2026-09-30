"""分位点回帰の 80% の幅の倍率を、検証データで決める。"""

from __future__ import annotations

import numpy as np

from .interval_width import IntervalWidth

#: 倍率の候補（0.50〜3.00 の 0.01 刻み。設計書 14 の「設定ファイルに書かないもの」）。
WIDTH_SCALES: np.ndarray = np.round(np.arange(0.50, 3.001, 0.01), 2)
#: 下の端より下（上の端より上）に外れてよい割合（10% と 90% の分位点なので、それぞれ 10%）。
TAIL_SHARE = 0.1


class IntervalWidthFitter:
    """倍率の候補から、下の端より下に外れた割合と、上の端より上に外れた割合が、それぞれ 10% にいちばん近いものを選ぶ。

    ``TemperatureFitter`` と同じく、学習に使っていない検証データ（早期終了に使っていない後半）で決める。
    下と上を別に決めるのは、外れ方が片側に偏っていても、両側を 10% ずつにそろえるためである。
    同じ近さの候補が複数あれば、小さい倍率（狭い幅）を選ぶ。
    """

    def fit(self, quantiles: np.ndarray, actual: np.ndarray) -> IntervalWidth:
        """``quantiles`` は行数 × 3（10%・50%・90%）、``actual`` は実際の値。値の無い行は数えない。"""
        ordered = np.sort(np.asarray(quantiles, dtype="float64"), axis=1)
        actual = np.asarray(actual, dtype="float64")
        usable = ~np.isnan(actual) & ~np.isnan(ordered).any(axis=1)
        low, middle, high = ordered[usable, 0], ordered[usable, 1], ordered[usable, 2]
        truth = actual[usable]
        below = [float(np.mean(truth < middle - scale * (middle - low))) for scale in WIDTH_SCALES]
        above = [float(np.mean(truth > middle + scale * (high - middle))) for scale in WIDTH_SCALES]
        return IntervalWidth(self._closest(below), self._closest(above))

    def _closest(self, shares: list[float]) -> float:
        gaps = np.abs(np.asarray(shares) - TAIL_SHARE)
        return float(WIDTH_SCALES[int(np.argmin(gaps))])
