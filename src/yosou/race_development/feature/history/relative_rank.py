"""順位を 0〜1 に直す。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import as_numbers


class RelativeRank:
    """順位と頭数から、0（先頭・いちばん速い・1着）〜 1（最後）の値を出す（設計書 04 の「分け方の決まり」）。

    ``(順位 − 1) ÷ (頭数 − 1)``。序盤の位置・4コーナーの位置・上がりの速さ・着順の位置の、ただ1つの置き場所。
    頭数が 1 以下か、順位が無ければ欠損値。
    """

    def of(self, rank: pd.Series, count: pd.Series) -> pd.Series:
        """``rank`` と ``count`` は同じ行の並び。戻り値も同じ行の並びと index。"""
        ranks, counts = as_numbers(rank), as_numbers(count)
        return ((ranks - 1) / (counts - 1)).where(counts > 1)
