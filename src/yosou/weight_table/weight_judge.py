"""体重の割引を、線で「体重の割引」と判定する。"""

from __future__ import annotations

import pandas as pd

from . import names

#: 線（3着以内の確率のポイント。設計書「買うレースと買い目を決める」07 の 3）。W がこれ以下なら「体重の割引」。
DEFAULT_LINE = -0.02


class WeightJudge:
    """W ≤ 線 を「体重の割引」、それ以外（欠損値も）を「－」にする。出馬表の表示と、危険な人気馬の理由に使う。"""

    def __init__(self, line: float = DEFAULT_LINE) -> None:
        self._line = line

    @property
    def line(self) -> float:
        return self._line

    def of(self, discount: pd.Series) -> pd.Series:
        verdict = pd.Series(names.NEUTRAL, index=discount.index, dtype="object")
        verdict[discount <= self._line] = names.DISCOUNTED
        return verdict
