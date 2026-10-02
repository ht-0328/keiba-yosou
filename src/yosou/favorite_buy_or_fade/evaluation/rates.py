"""率を表の文字にする。"""

from __future__ import annotations

import pandas as pd


def rate(values: pd.Series) -> str:
    """値の平均を百分率の文字にする（0 と 1 の列なら割合、払戻 ÷ 100 の列なら回収率）。行が無ければ空。"""
    return percent(values.mean()) if len(values) else ""


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"
