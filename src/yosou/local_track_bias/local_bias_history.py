"""過去の地方の出走に、年ごとのリーク防止で当日の馬場傾向（U）を付ける（学習と確かめ用）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import PredictionTiming
from yosou.track_bias import RaceSlopes, YearlyBias

from .front_position import FrontPosition


class LocalBiasHistory:
    """``runs``（``BiasRunRepository`` の表。地方の元DB なら地方の全出走）から、レースごとの傾き（``RaceSlopes``）と
    馬ごとの前らしさの見込み（``FrontPosition``）を出し、``YearlyBias`` で出走ごとに U を付ける。

    中央の ``BiasHistory`` と同じ形で、展開の年ごとの確かめの予測の代わりに直近3走の位置を使う。
    学習データには、レースの年ごとに「その年の1月1日より前のレースだけで作った過去の傾きの表」と、
    そのレースより前に終わったレース（当日の先のレース・前の日のレース）の傾きで付ける（リークを防ぐ）。
    """

    def __init__(self) -> None:
        self._slopes = RaceSlopes()
        self._front = FrontPosition()
        self._yearly = YearlyBias()

    def of(self, timing: PredictionTiming, runs: pd.DataFrame, slopes: pd.DataFrame | None = None) -> pd.DataFrame:
        """1行 = 1頭（``BiasCorrection.COLUMNS`` と ``race_date``）。``slopes`` を渡せば（``RaceSlopes.of(runs)`` を先に出してあれば）それを使う。"""
        if slopes is None:
            slopes = self._slopes.of(runs)
        corrected = self._yearly.of(self._front.of(runs), runs, slopes, timing)
        return corrected[corrected["race_date"].notna()].reset_index(drop=True)
