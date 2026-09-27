"""1回の走のスピード指数。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .pace_balance import PACE
from .standard_table import COURSE_STANDARD, TRACK_VARIANT

#: 出力の列。
FIGURE = "スピード指数"
#: 点数の中心と、1% あたりの点数。基準の水準（1勝クラス・古馬）の、ふつうの馬場でのふつうの走が 80点。
_CENTER, _POINTS_PER_PERCENT = 80.0, 10.0
#: 斤量の基準（kg）。
_BASE_WEIGHT = 55.0


class SpeedFigure:
    """出走の表（レースの表の コースの基準・馬場差・ペース を付けたもの）に、スピード指数の列を足す。

    速さ（%）= コースの基準 + 馬場差 − 走破タイムの対数 × 100 + 斤量補正 − ペース補正
    スピード指数 = 80 + 速さ × 10

    - レースの水準の差は引かない。強いレースで速く走った馬ほど、指数が高くなる（それが能力の差だから）。
    - 斤量補正 = ``weight_per_kg`` ×（斤量 − 55kg）。重く背負ったほど足す。
    - ペース補正 = ``pace_offsets`` の（脚質, ペース）の値。無ければ 0。
    - ``track_variant`` が False なら、馬場差を足さない（比べるため）。
    - ``floor_gap`` があれば、そのレースでいちばん高い指数より ``floor_gap`` 点以上低い指数を、その線まで切り上げる。
    例: 基準 96.0秒相当のコースで、馬場差 −0.5%（速い馬場）の日に 95.3秒で走り、55kg なら、
    速さ = 0.73 − 0.5 = 0.23% で、指数は 82.3。
    着順の付かなかった走（競走中止など）と、走破タイムの無い走は欠損値。
    """

    def __init__(self, weight_per_kg: float, pace_offsets: pd.Series | None = None, *,
                 track_variant: bool = True, floor_gap: float | None = None) -> None:
        self._weight_per_kg = weight_per_kg
        self._pace_offsets = pace_offsets
        self._track_variant = track_variant
        self._floor_gap = floor_gap

    def build(self, runs: pd.DataFrame) -> pd.DataFrame:
        time = runs["finish_time"].where(runs["finish"].notna() & (runs["finish_time"] > 0))
        variant = runs[TRACK_VARIANT] if self._track_variant else 0.0
        speed = runs[COURSE_STANDARD] + variant - 100 * np.log(time.astype(float))
        speed = speed + self._weight_per_kg * (runs["carried"].astype(float) - _BASE_WEIGHT)
        figure = _CENTER + _POINTS_PER_PERCENT * (speed - self._pace(runs))
        return runs.assign(**{FIGURE: self._floored(figure, runs["race_id"])})

    def _floored(self, figure: pd.Series, race_id: pd.Series) -> pd.Series:
        if self._floor_gap is None:
            return figure
        floor = figure.groupby(race_id).transform("max") - self._floor_gap
        return figure.where(figure.isna() | (figure >= floor), floor)

    def _pace(self, runs: pd.DataFrame) -> pd.Series:
        if self._pace_offsets is None:
            return pd.Series(0.0, index=runs.index)
        index = pd.MultiIndex.from_frame(runs[["style", PACE]])
        return pd.Series(self._pace_offsets.reindex(index).fillna(0.0).to_numpy(), index=runs.index)
