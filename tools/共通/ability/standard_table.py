"""求めたコースの基準とレースの水準の差を、レースに当てはめる。"""

from __future__ import annotations

import pandas as pd

from .race_table import FIELD_LEVEL, MEDIAN_LOG_TIME

#: コースの鍵と、馬場差の鍵。
COURSE_KEY: tuple[str, ...] = ("venue_code", "track_code", "distance_m")
DAY_KEY: tuple[str, ...] = ("race_date", "venue_code", "surface")
#: 水準の差を 0 とするレースの水準。
REFERENCE_LEVEL = "1勝クラス・古馬"
#: 出力の列（どれも、タイムの対数 × 100 の単位。1 はおよそ 1%）。
COURSE_STANDARD, LEVEL_GAP, TRACK_VARIANT = "コースの基準", "水準の差", "馬場差"


class StandardTable:
    """``SpeedStandard`` が求めた、コースの基準（``course``）とレースの水準の差（``level``）。

    ``apply`` で、レースの表に3つの列を足す。馬場差は、その日・その競馬場・その芝ダのレースの
    「中央値タイムの対数 − コースの基準 − 水準の差」の平均で、その日のレースから求め直す（求めた期間の後の日にも付く）。
    コースの基準が無いコース（求めた期間に無かった距離など）は、3つとも欠損値。
    """

    def __init__(self, course: pd.Series, level: pd.Series) -> None:
        self._course = course
        self._level = level

    def apply(self, races: pd.DataFrame) -> pd.DataFrame:
        course_index = pd.MultiIndex.from_frame(races[list(COURSE_KEY)])
        course = pd.Series(self._course.reindex(course_index).to_numpy(), index=races.index)
        level = races[FIELD_LEVEL].map(self._level).astype(float)
        residual = races[MEDIAN_LOG_TIME] - course - level
        variant = residual.groupby([races[key] for key in DAY_KEY]).transform("mean")
        return races.assign(**{COURSE_STANDARD: course, LEVEL_GAP: level, TRACK_VARIANT: variant})
