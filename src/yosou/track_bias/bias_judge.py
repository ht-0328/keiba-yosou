"""バイアスの補正を、線で「バイアス向き」「バイアス逆」に分ける。"""

from __future__ import annotations

import pandas as pd

from . import names

#: 線（3着以内の確率のポイント。設計書「買うレースと買い目を決める」06 の 1）。B がこれ以上なら向き、−これ以下なら逆。
DEFAULT_LINE = 0.02


class BiasJudge:
    """B ≥ +線 を「バイアス向き」、B ≤ −線 を「バイアス逆」、それ以外（欠損値も）を「－」にする。

    出馬表に見せるための判定で、確率の補正そのものは B の値でモデルに渡す（判定は渡さない）。
    「バイアス逆」は、危険な人気馬の理由の1つ（設計書 07 の 3）。
    """

    def __init__(self, line: float = DEFAULT_LINE) -> None:
        self._line = line

    def of(self, correction: pd.Series) -> pd.Series:
        verdict = pd.Series(names.NEUTRAL, index=correction.index, dtype="object")
        verdict[correction >= self._line] = names.WITH_BIAS
        verdict[correction <= -self._line] = names.AGAINST_BIAS
        return verdict
