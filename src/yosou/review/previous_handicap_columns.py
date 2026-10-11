"""出走ごとに、その馬の前走（と前々走）の不利を列にする。"""

from __future__ import annotations

import pandas as pd

from . import names
from .features import PREVIOUS_BIAS, PREVIOUS_HANDICAP_NAMES, PREVIOUS_LATE_START, PREVIOUS_MAX, PREVIOUS_PACE, PREVIOUS_REVIEW

#: 鍵。
_KEY: list[str] = [names.RACE_ID, names.HORSE_ID]


class PreviousHandicapColumns:
    """不利の表（``RunHandicaps`` の表。全部の出走の行を持ち、不利の無い走は程度 0）から、出走ごとに前走の不利の程度（3種類）・
    前走を見直すか・近2走の程度の最大を出す（まとまり X）。

    馬ごとに開催日の順に並べ、1つ前（と2つ前）の走の値を取る。前走が無い馬（新馬など）は欠損値。前走の不利が判定できなかった
    （最初のコーナーの記録が無いなど）走は、その種類だけ欠損値。
    """

    def of(self, handicaps: pd.DataFrame) -> pd.DataFrame:
        """列は ``race_id``・``horse_id`` と ``PREVIOUS_HANDICAP_NAMES``。1行 = 1頭。"""
        ordered = handicaps.sort_values([names.HORSE_ID, names.RACE_DATE, names.RACE_ID], kind="stable")
        horse = ordered[names.HORSE_ID]
        previous = ordered[list(names.DEGREES)].groupby(horse).shift(1)
        before_previous = ordered[list(names.DEGREES)].groupby(horse).shift(2)
        review = (previous.max(axis=1) >= 2).astype("float64").where(previous.notna().any(axis=1))
        recent_max = pd.concat([previous.max(axis=1), before_previous.max(axis=1)], axis=1).max(axis=1)
        table = pd.DataFrame({
            names.RACE_ID: ordered[names.RACE_ID].astype(str), names.HORSE_ID: ordered[names.HORSE_ID].astype(str),
            PREVIOUS_LATE_START: previous[names.LATE_START_DEGREE], PREVIOUS_PACE: previous[names.PACE_DEGREE],
            PREVIOUS_BIAS: previous[names.BIAS_DEGREE], PREVIOUS_REVIEW: review, PREVIOUS_MAX: recent_max,
        }, index=ordered.index)
        return table.reindex(handicaps.index)[[*_KEY, *PREVIOUS_HANDICAP_NAMES]]
