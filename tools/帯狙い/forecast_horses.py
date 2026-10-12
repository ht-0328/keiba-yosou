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
    """

    def of(self, forecast: dict[str, Any]) -> RaceHorses:
        horses = [horse for horse in forecast["horses"] if horse.get(columns.HORSE_NO) is not None]
        numbers = np.array([int(horse[columns.HORSE_NO]) for horse in horses])
        top3 = np.array([float(horse.get(columns.PROBABILITY) or 0.0) for horse in horses])
        wins = [horse.get(columns.WIN_PROBABILITY) for horse in horses]
        win = np.array([float(value) for value in wins]) if all(value is not None for value in wins) else top3.copy()
        total = win.sum()
        return RaceHorses(forecast["rid"], numbers, win / total if total > 0 else win, top3)
