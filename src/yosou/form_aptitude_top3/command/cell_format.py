"""表のセルに入れる値の形をそろえる関数。"""

from __future__ import annotations

import math

import pandas as pd

#: 表に出す小数の桁数。
_DIGITS = 3


def rounded(value: float | None) -> float | None:
    """小数を3桁に丸める。値が無ければ（None か NaN）空欄にする。"""
    if value is None or math.isnan(value):
        return None
    return round(float(value), _DIGITS)


def day_text(value: pd.Timestamp) -> str:
    """日付を YYYY-MM-DD にする。"""
    return pd.Timestamp(value).date().isoformat()


def horse_no_text(value: float) -> int | None:
    """馬番を整数にする。決まっていなければ（木曜の出走馬名表）空欄にする。"""
    if pd.isna(value):
        return None
    return int(value)
