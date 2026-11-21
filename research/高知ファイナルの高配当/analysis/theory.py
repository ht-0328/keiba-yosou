"""理論: 「こういう馬は同じ人気の馬より来る／来ない」を、言葉と、ファイナルレースの出走馬の表に当てる条件で持つ。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Theory:
    """1つの条件。``group`` は理論の番号（①〜⑤）か、確かめただけの材料の区分。``condition`` は出走馬の表 → 当てはまる行の bool。"""

    group: str
    name: str
    condition: Callable[[pd.DataFrame], pd.Series]

    def applies(self, table: pd.DataFrame) -> pd.Series:
        """当てはまる行が真の列。材料が欠けている行は当てはまらないとする。"""
        return self.condition(table).fillna(False).astype(bool)
