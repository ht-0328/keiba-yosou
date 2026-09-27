"""期待値の線を前半の年で決め、後半の年で確かめる。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..backtest.staked_payback import PaybackSummary, StakedPayback

#: 線を決める年（前半）と、確かめる年（後半）。複勝の線を決めたときと同じ分け方。
EARLY_YEARS = (2019, 2021)
LATE_YEARS = (2022, 2026)
#: 試す線。
LINES: tuple[float, ...] = (1.0, 1.1, 1.2, 1.3, 1.4, 1.5)
#: 線を選ぶときに、前半で要る当たりの数。少ない当たりで決まった回収率は当てにならない。
MIN_EARLY_HITS = 30


@dataclass(frozen=True)
class LineResult:
    """1つの線の、前半と後半の成績。"""

    line: float
    early: PaybackSummary
    late: PaybackSummary


@dataclass(frozen=True)
class StudyResult:
    """線ごとの成績と、選んだ線・採否。"""

    lines: tuple[LineResult, ...]
    chosen: LineResult | None

    @property
    def adopted(self) -> bool:
        """後半で、回収率が 100% を超え、90% の幅の下の端も 100% を超えたか。"""
        return (self.chosen is not None and self.chosen.late.rate > 100
                and self.chosen.late.low > 100)


class LineStudy:
    """買い目の表（1行 = 1点）に線を当て、線ごとの成績を出して、前半だけで線を選ぶ。

    入力の列: rid・year・day・ev（期待値）・payout（100円あたりの払戻）・stake（賭け金、円）。
    ``cap`` があれば、1レースで期待値の高い順に ``cap`` 点まで残す。
    線の選び方: 前半の当たりが ``MIN_EARLY_HITS`` 以上ある線のうち、前半の回収率がいちばん高い線。
    後半の結果は、線を選ぶのに使わない。
    """

    def __init__(self, payback: StakedPayback | None = None) -> None:
        self._payback = payback or StakedPayback()

    def run(self, tickets: pd.DataFrame, cap: int | None) -> StudyResult:
        results = tuple(self._line(tickets, line, cap) for line in LINES)
        usable = [result for result in results if result.early.hits >= MIN_EARLY_HITS]
        chosen = max(usable, key=lambda result: result.early.rate, default=None)
        return StudyResult(results, chosen)

    def _line(self, tickets: pd.DataFrame, line: float, cap: int | None) -> LineResult:
        bought = self.select(tickets, line, cap)
        return LineResult(line, self._period(bought, EARLY_YEARS), self._period(bought, LATE_YEARS))

    def select(self, tickets: pd.DataFrame, line: float, cap: int | None) -> pd.DataFrame:
        """期待値が線以上の買い目。``cap`` があれば1レースで期待値の高い順にその点数まで。"""
        bought = tickets[tickets["ev"] >= line]
        if cap is None:
            return bought
        ranked = bought.sort_values(["rid", "ev"], ascending=[True, False])
        return ranked[ranked.groupby("rid").cumcount() < cap]

    def _period(self, bought: pd.DataFrame, years: tuple[int, int]) -> PaybackSummary:
        rows = bought[bought["year"].between(*years)]
        return self._payback.summarize(rows["day"], rows["stake"], rows["payout"])
