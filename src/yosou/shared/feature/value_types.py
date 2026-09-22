"""列の値の型をそろえる関数。"""

from __future__ import annotations

import pandas as pd

_YES, _NO = "はい", "いいえ"


def as_numbers(values: pd.Series) -> pd.Series:
    """数の列を小数の列にする。DuckDB の整数の欠損値（<NA>）を、pandas の NaN にそろえる。"""
    return pd.to_numeric(values, errors="coerce").astype("float64")


def as_yes_no(values: pd.Series) -> pd.Series:
    """真偽値の列を「はい」「いいえ」にする。分からなければ欠損値。"""
    return values.map({True: _YES, False: _NO})
