"""成績の表のセルの書き方（関数だけ）。"""

from __future__ import annotations

import math

#: 値を出せないセル（買った点が無いなど）。
BLANK = "-"


def rate_text(rate: float) -> str:
    """割合や回収率。例: 1.123 → ``112.3%``。出せなければ ``-``。"""
    return BLANK if math.isnan(rate) else f"{rate:.1%}"


def number_text(value: float, digits: int = 1) -> str:
    """小数。例: 12.34 → ``12.3``。出せなければ ``-``。"""
    return BLANK if math.isnan(value) else f"{value:,.{digits}f}"


def yen_text(value: float) -> str:
    """金額。例: 12345.6 → ``12,346円``。出せなければ ``-``。"""
    return BLANK if math.isnan(value) else f"{value:,.0f}円"


def signed_yen_text(value: float) -> str:
    """収支。例: -1200 → ``-1,200円``、3400 → ``+3,400円``。出せなければ ``-``。"""
    return BLANK if math.isnan(value) else f"{value:+,.0f}円"
