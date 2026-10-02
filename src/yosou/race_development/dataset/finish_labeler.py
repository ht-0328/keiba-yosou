"""⑦ 1着の目的変数を付ける。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import as_numbers

from . import label_names as names


class FinishLabeler:
    """⑦ 1着（1/0）を付ける（設計書 06 の図6・10 の 10.）。評価用に確定着順も返す。

    1着が2頭以上のレース（同着）は、1レースに正解が1つの形にならないので、全頭を欠損値にする。
    競走中止・失格の馬（確定着順が無い）は 0。1着の馬がいないレース（成績の無い予測のレースなど）も欠損値にする。
    """

    def build(self, samples: pd.DataFrame) -> pd.DataFrame:
        """列は ``1着``・``確定着順``。行の並びと index は ``samples`` と同じ。"""
        finish = as_numbers(samples["finish"])
        is_winner = (finish == 1).astype("float64")
        winners = is_winner.groupby(samples["race_id"]).transform("sum")
        return pd.DataFrame({
            names.WINNER: is_winner.where(winners == 1),
            names.FINISH: finish,
        }, index=samples.index)
