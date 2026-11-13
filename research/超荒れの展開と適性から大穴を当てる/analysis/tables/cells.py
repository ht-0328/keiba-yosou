"""表のセルの書き方（割合・ポイント）。"""

from __future__ import annotations

import math


def percent(numerator: float, denominator: float, digits: int = 1) -> str:
    """割合を ``12.3%`` の形で。分母が 0 なら空。"""
    if not denominator:
        return ""
    return f"{numerator / denominator * 100:.{digits}f}%"


def points(value: float, std_error: float | None = None) -> str:
    """割合の差をポイントで ``+1.2`` の形に（標準誤差があれば ``+1.2 ±0.4``）。欠損値なら空。"""
    if value is None or math.isnan(value):
        return ""
    text = f"{value * 100:+.2f}"
    if std_error is not None and not math.isnan(std_error):
        text += f" ±{std_error * 100:.2f}"
    return text


def ratio(numerator: float, denominator: float) -> str:
    """比を ``1.23`` の形で。分母が 0 なら空。"""
    if not denominator:
        return ""
    return f"{numerator / denominator:.2f}"
