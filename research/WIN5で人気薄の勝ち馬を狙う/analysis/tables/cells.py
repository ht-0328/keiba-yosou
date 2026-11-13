"""表のセルの書き方（割合・比・小数）。"""

from __future__ import annotations

import math


def percent(numerator: float, denominator: float) -> str:
    """割合を ``12.3%`` の形で。分母が 0 なら空。"""
    if not denominator:
        return ""
    return f"{numerator / denominator * 100:.1f}%"


def ratio(numerator: float, denominator: float) -> str:
    """比を ``1.23`` の形で。分母が 0 なら空。"""
    if not denominator:
        return ""
    return f"{numerator / denominator:.2f}"


def number(value: float, digits: int = 2) -> str:
    """小数を丸めて。欠損値なら空。"""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return f"{value:.{digits}f}"
