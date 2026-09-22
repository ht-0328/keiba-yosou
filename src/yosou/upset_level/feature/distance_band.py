"""距離を距離帯にする。"""

from __future__ import annotations

import pandas as pd

#: 距離帯の区切り（出走別着度数と同じ。1200m以下、1201〜1400m、…、2801m以上）。
_BAND_EDGES_M: tuple[int, ...] = (1200, 1400, 1600, 1800, 2000, 2200, 2400, 2800)
_BAND_NAMES: tuple[str, ...] = (
    "1200以下", "1201-1400", "1401-1600", "1601-1800", "1801-2000", "2001-2200", "2201-2400", "2401-2800", "2801以上",
)


def distance_band(distance_m: pd.Series) -> pd.Series:
    """距離（m）の列を、距離帯の名前の列にする。距離が無ければ欠損値。"""
    bins = [-float("inf"), *_BAND_EDGES_M, float("inf")]
    bands = pd.cut(pd.to_numeric(distance_m, errors="coerce"), bins=bins, labels=_BAND_NAMES, right=True)
    return bands.astype("object").where(bands.notna())
