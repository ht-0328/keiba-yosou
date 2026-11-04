"""理論: 「こういう事情の人気馬は崩れる」「こういう事情の穴馬は来る」を、言葉と、出走の表に当てる条件で持つ。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

#: 理論の種類。
FAVORITE_FAILS = "人気馬が崩れる"
FAVORITE_HOLDS = "人気馬が信頼できる"
LONGSHOT_COMES = "穴馬が来る"
LONGSHOT_FAILS = "穴馬が来ない"


@dataclass(frozen=True)
class Theory:
    """1つの理論。``condition`` は出走の表（帯と事情が付いたもの）→ 当てはまる行の bool。``bands`` はこの理論を数える人気の帯。"""

    name: str
    kind: str
    bands: tuple[str, ...]
    meaning: str
    condition: Callable[[pd.DataFrame], pd.Series]

    def applies(self, table: pd.DataFrame) -> pd.Series:
        return self.condition(table).fillna(False).astype(bool)
