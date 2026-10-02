"""横に並べた過去走の値の、平均・最小・ばらつきなど。"""

from __future__ import annotations

import warnings

import numpy as np

#: 日数の重みの半減期（日）。180日前の走は半分の重み（設計書 09 の K）。
HALF_LIFE_DAYS = 180.0
#: ばらつきを出すのに要る走の数。1走だけのばらつきは 0 ではなく欠損値にする（「いつも同じ」に見えないように）。
_MIN_RUNS_FOR_SPREAD = 2


class LagStatistics:
    """``RunLags`` の行列（出走の行の数 × 走の数。列 0 がいちばん新しい走）から、行ごとの値を出す。

    欠損値（走が足りない・値が無い）は数えない。数える値が1つも無い行は欠損値にする。
    """

    def mean(self, values: np.ndarray, runs: int) -> np.ndarray:
        """新しい ``runs`` 走の平均。"""
        return self._quiet(np.nanmean, values[:, :runs])

    def minimum(self, values: np.ndarray, runs: int) -> np.ndarray:
        """新しい ``runs`` 走の最小。"""
        return self._quiet(np.nanmin, values[:, :runs])

    def spread(self, values: np.ndarray, runs: int) -> np.ndarray:
        """新しい ``runs`` 走の標準偏差（不偏）。2走未満は欠損値。"""
        part = values[:, :runs]
        spread = self._quiet(lambda array, axis: np.nanstd(array, axis=axis, ddof=1), part)
        return np.where(self.count(part, runs) >= _MIN_RUNS_FOR_SPREAD, spread, np.nan)

    def count(self, values: np.ndarray, runs: int) -> np.ndarray:
        """新しい ``runs`` 走のうち、値のある走の数。"""
        return np.sum(~np.isnan(values[:, :runs].astype("float64")), axis=1).astype("float64")

    def total(self, values: np.ndarray, runs: int) -> np.ndarray:
        """新しい ``runs`` 走の合計（値のある走だけ。無ければ 0）。"""
        return np.nansum(values[:, :runs].astype("float64"), axis=1)

    def weighted_mean(self, values: np.ndarray, days_ago: np.ndarray) -> np.ndarray:
        """今回の開催日からの日数で重みを付けた平均。重みは ``2^(−日数 ÷ 180)``。"""
        present = ~np.isnan(values)
        weights = np.where(present, 2.0 ** (-days_ago / HALF_LIFE_DAYS), 0.0)
        weight_sum = weights.sum(axis=1)
        weighted = np.nansum(np.where(present, values, 0.0) * weights, axis=1)
        return np.where(weight_sum > 0, weighted / np.where(weight_sum > 0, weight_sum, 1.0), np.nan)

    def masked_mean(self, values: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """``mask`` が真の走だけの平均（例: 今回と同じ芝ダの走だけ）。"""
        return self._quiet(np.nanmean, np.where(mask, values, np.nan))

    def _quiet(self, function, values: np.ndarray) -> np.ndarray:
        """全部が欠損値の行で出る警告（Mean of empty slice など）を出さずに計算する。結果は欠損値になる。"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            return function(values.astype("float64"), axis=1)
