"""名前の付いた真偽の決まり1つ（手がかり・馬の型・レースの型に共通の形）。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class FlagRule:
    """``name`` は表に出す名前、``group`` はまとまり（前走・条件替わり・人 …）、``description`` は言葉での定義。
    ``rule`` は出走の表（またはレースの表）を受け取り、行ごとの真偽を返す。欠損値は偽にする。"""

    name: str
    group: str
    description: str
    rule: Callable[[pd.DataFrame], pd.Series]

    def flags(self, frame: pd.DataFrame) -> pd.Series:
        return self.rule(frame).fillna(False).astype(bool)
