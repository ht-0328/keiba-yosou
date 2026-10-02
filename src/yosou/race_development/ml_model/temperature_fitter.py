"""レースの中でそろえるときの温度を決める。"""

from __future__ import annotations

import numpy as np

from .race_softmax import RaceSoftmax

#: 温度の候補（0.50〜2.00 の 0.01 刻み。設計書 14 の「設定ファイルに書かないもの」）。
TEMPERATURES: np.ndarray = np.round(np.arange(0.50, 2.001, 0.01), 2)
#: ログを取るときに 0 にならないようにする下限。
_FLOOR = 1e-12


class TemperatureFitter:
    """温度の候補から、レースごとのログ損失がいちばん小さいものを選ぶ（設計書 03 の 2・10 の 2.）。

    レースごとのログ損失は、正解の馬（先頭か1着の馬）に付けた確率 p の ``−log(p)`` の平均。
    """

    def __init__(self) -> None:
        self._softmax = RaceSoftmax()

    def fit(self, raw: np.ndarray, race_ids: np.ndarray, is_answer: np.ndarray) -> float:
        """``is_answer`` は正解の馬なら 1。どれも同じ長さ。"""
        answers = np.asarray(is_answer) == 1
        losses = [self._loss(self._softmax.apply(raw, race_ids, temperature), answers) for temperature in TEMPERATURES]
        return float(TEMPERATURES[int(np.argmin(losses))])

    def _loss(self, probability: np.ndarray, answers: np.ndarray) -> float:
        return float(-np.log(np.clip(probability[answers], _FLOOR, 1.0)).mean())
