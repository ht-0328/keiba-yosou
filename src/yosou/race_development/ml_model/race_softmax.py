"""raw スコアを、レースごとに合計 1 の確率に直す。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 確率を raw スコアに戻すときに、0 と 1 にぴったり付かないようにする幅。
_EPSILON = 1e-9


class RaceSoftmax:
    """raw スコアを温度で割り、レースIDごとにソフトマックスで合計 1 の確率にする（設計書 03 の 2）。"""

    def apply(self, raw: np.ndarray, race_ids: np.ndarray, temperature: float) -> np.ndarray:
        """``raw`` と ``race_ids`` は同じ長さ。戻り値も同じ長さで、同じレースの値を足すと 1。"""
        scaled = pd.Series(np.asarray(raw, dtype="float64") / temperature)
        races = pd.Series(np.asarray(race_ids))
        shifted = scaled - scaled.groupby(races).transform("max")  # 大きな数の exp であふれないよう、レースの最大を引く
        exponent = np.exp(shifted)
        return (exponent / exponent.groupby(races).transform("sum")).to_numpy()

    def raw_of(self, probability: np.ndarray) -> np.ndarray:
        """二値分類の確率を raw スコア（``log(p / (1 − p))``）に戻す。"""
        clipped = np.clip(np.asarray(probability, dtype="float64"), _EPSILON, 1 - _EPSILON)
        return np.log(clipped / (1 - clipped))
