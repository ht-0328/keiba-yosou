"""第1段: レースを選ぶ点数。"""

from __future__ import annotations


class RaceSelectionScore:
    """荒れ具合の予想の3連単が 1,000倍以上になる確率（大荒れ＋超荒れ）と、予想が見た 1,000倍以上になる確率
    （``BigPayoutChance``）の平均（設計書 15 の 1）。

    予想が見た確率が無いとき（組ごとのオッズがまだ無い木曜・前日、今の予想を出せないレース）は、荒れ具合の予想の確率だけ。
    線（既定 0.40）以上のレースを「荒れる」と決めて買う。
    """

    def of(self, upset_probability: float, chance: float | None) -> float:
        if chance is None:
            return float(upset_probability)
        return (float(upset_probability) + float(chance)) / 2.0
