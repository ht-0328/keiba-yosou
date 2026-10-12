"""今週の予想の形の結果から、買い目を組むための出走馬ごとの予想を取り出す。"""

from __future__ import annotations

from typing import Any

import numpy as np

from yosou.upset_premise.betting import RaceHorses

from 今週の予想 import forecast_columns as columns


class ForecastHorses:
    """``RaceForecaster.forecast`` の結果（荒れる前提のモデルで出したもの）の ``horses`` から、馬番・1着の確率・3着以内の確率を取り出す。

    消（危険な人気馬）の印の馬も、買い目の候補から外さない（荒れる前提の予想は、人気馬を下げることを学んでいるため）。
    1着の確率はレースで合計 1 に直す（組の確率を Harville の式で作るため）。1着の確率が無ければ（木曜）、3着以内の確率で代わりにする。
    ``usual`` は同じレースを今の予想（手本のモデル）で出した結果。渡すと、その3着以内の確率を馬番で突き合わせて
    ``RaceHorses.usual_top3`` に入れる（一律の買い方の2着・3着の重み。設計書 15 の 6）。1頭でも無ければ入れない。
    """

    def of(self, forecast: dict[str, Any], usual: dict[str, Any] | None = None) -> RaceHorses:
        horses = [horse for horse in forecast["horses"] if horse.get(columns.HORSE_NO) is not None]
        numbers = np.array([int(horse[columns.HORSE_NO]) for horse in horses])
        top3 = np.array([float(horse.get(columns.PROBABILITY) or 0.0) for horse in horses])
        wins = [horse.get(columns.WIN_PROBABILITY) for horse in horses]
        win = np.array([float(value) for value in wins]) if all(value is not None for value in wins) else top3.copy()
        total = win.sum()
        return RaceHorses(forecast["rid"], numbers, win / total if total > 0 else win, top3, self._usual_top3(numbers, usual))

    @staticmethod
    def _usual_top3(numbers: np.ndarray, usual: dict[str, Any] | None) -> np.ndarray | None:
        """今の予想の3着以内の確率を、馬番の並びにそろえる。無い馬番があれば None。"""
        if usual is None:
            return None
        by_number = {int(horse[columns.HORSE_NO]): horse.get(columns.PROBABILITY)
                     for horse in usual["horses"] if horse.get(columns.HORSE_NO) is not None}
        values = [by_number.get(int(number)) for number in numbers]
        if any(value is None for value in values):
            return None
        return np.array([float(value) for value in values])
