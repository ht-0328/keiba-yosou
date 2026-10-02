"""買い目の確率を、オッズの帯ごとの実績で直す（較正）。"""

from __future__ import annotations

import numpy as np


class OddsBandCalibrator:
    """オッズの帯ごとに「実際に当たった数 ÷ 確率の合計」を数え、確率に掛ける倍率にする。

    Harville の式で出した組み合わせの確率は、人気薄の組ほど大きすぎることが多い。
    帯ごとの実績の比を掛けると、その帯の確率の平均が実際の当たり方にそろう。

    ``shrink`` は、当たりの見込みが少ない帯の倍率を 1 に寄せる強さ（見込みの当たりの数で数える）。
    例: 見込み 5回・実際 1回の帯は、(1 + 20) ÷ (5 + 20) = 0.84倍。見込み 500回・実際 400回なら 0.81倍。
    評価する年の前の年までの実績だけで数える（``add`` は年を評価し終えてから呼ぶ）。
    """

    def __init__(self, bands: tuple[float, ...], shrink: float = 20.0) -> None:
        self._bands = np.asarray(bands, dtype=float)
        self._shrink = shrink
        size = len(bands) - 1
        self._expected = np.zeros(size)
        self._actual = np.zeros(size)

    def add(self, odds: np.ndarray, probability: np.ndarray, hit: np.ndarray) -> None:
        """1年ぶんの買い目の、確率と当たったか（1 か 0）を足す。"""
        band = self._band(odds)
        size = len(self._expected)
        self._expected += np.bincount(band, weights=probability, minlength=size)
        self._actual += np.bincount(band, weights=hit, minlength=size)

    def factors(self, odds: np.ndarray) -> np.ndarray:
        """買い目ごとの、確率に掛ける倍率。"""
        ratio = (self._actual + self._shrink) / (self._expected + self._shrink)
        return ratio[self._band(odds)]

    def _band(self, odds: np.ndarray) -> np.ndarray:
        index = np.searchsorted(self._bands, np.asarray(odds, dtype=float), side="right") - 1
        return np.clip(index, 0, len(self._expected) - 1)
