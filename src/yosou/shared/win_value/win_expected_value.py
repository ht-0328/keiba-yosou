"""単勝を買う期待値を出す。"""

from __future__ import annotations

import pandas as pd

from ..feature import as_numbers

#: 出す列の名前（予測の結果の表にも、そのまま出す）。
WIN_VALUE = "単勝の期待値"


class WinExpectedValue:
    """1着になる確率と単勝オッズから、単勝を買う期待値を出す。

    期待値 = 1着になる確率 × 単勝オッズ（1 で元返し。1.2 なら 100円あたり平均 120円戻る見込み）。
    例: 1着になる確率 0.21・単勝 6.0倍なら、0.21 × 6.0 = 1.26。
    単勝オッズの無い馬（木曜・無投票）は欠損値。
    """

    def of(self, win_probability: pd.Series, win_odds: pd.Series) -> pd.Series:
        """行の並びと index は ``win_probability`` と同じ。"""
        odds = as_numbers(win_odds).set_axis(win_probability.index)
        values = win_probability.astype(float) * odds.where(odds > 0)
        return values.rename(WIN_VALUE)
