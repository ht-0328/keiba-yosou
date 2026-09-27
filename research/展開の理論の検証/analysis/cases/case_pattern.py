"""事例の型（どんなレースを集めるか）。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class CasePattern:
    """集める事例の型。``matches`` は1行 = 1レースの表を受け取り、当てはまるレースで True の列を返す。

    例: 名前「ハイで前が勝った」、理論との関係「反する」、``matches`` = ペースがハイで勝ち馬の脚質が逃げか先行。
    """

    key: str
    name: str
    relation: str
    matches: Callable[[pd.DataFrame], pd.Series]
