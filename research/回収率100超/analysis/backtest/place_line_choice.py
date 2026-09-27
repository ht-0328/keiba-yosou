"""複勝を買う期待値の線を、決まりどおりに前半の年だけで選ぶ。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .staked_payback import PaybackSummary, StakedPayback

#: 線を決める年（前半）と、確かめる年（後半）。
EARLY_YEARS = (2019, 2021)
LATE_YEARS = (2022, 2026)
#: 試す線。
PLACE_LINES: tuple[float, ...] = (1.00, 1.05, 1.10, 1.15, 1.20, 1.25, 1.30, 1.40)
#: 前半の1年あたりに残ってほしい買い目の数。これより少ない線は、回収率が高くても選ばない。
MIN_YEARLY_BETS = 300


@dataclass(frozen=True)
class PlaceLineResult:
    """1つの線の、前半と後半の成績。"""

    line: float
    early: PaybackSummary
    late: PaybackSummary

    @property
    def early_yearly_bets(self) -> float:
        return self.early.bets / (EARLY_YEARS[1] - EARLY_YEARS[0] + 1)

    @property
    def qualifies(self) -> bool:
        """前半で回収率が 100% を超え、1年あたり ``MIN_YEARLY_BETS`` 点以上残るか。"""
        return self.early.rate > 100 and self.early_yearly_bets >= MIN_YEARLY_BETS


@dataclass(frozen=True)
class PlaceLineStudy:
    """線ごとの成績と、決まりで選んだ線。"""

    lines: tuple[PlaceLineResult, ...]
    chosen: PlaceLineResult | None


class PlaceLineChoice:
    """複勝の買い目の表（1行 = 1点）に線を当て、線ごとの成績を出して、前半だけで線を選ぶ。

    入力の列: year・day・ev（期待値）・payout（100円あたりの払戻）。1点 100円で数える。
    決まり: 前半で回収率が 100% を超え、前半の1年あたりの買い目が ``MIN_YEARLY_BETS`` 点以上残る線のうち、
    前半の回収率がいちばん高い線。後半の結果は、線を選ぶのに使わない。

    点数の条件を置くのは、線を上げるほど買い目が減り、少ない買い目で出た高い回収率は偶然の分が大きいためである。
    研究「複勝以外の回収率100超」などで使う ``tickets.LineStudy`` は、券種どうしを同じ物差しで比べるための
    別の決まり（前半の当たりが 30 以上のうち回収率がいちばん高い線）で、実際に買う線はこちらで決める。
    """

    def __init__(self, payback: StakedPayback | None = None) -> None:
        self._payback = payback or StakedPayback()

    def run(self, tickets: pd.DataFrame) -> PlaceLineStudy:
        results = tuple(self._line(tickets, line) for line in PLACE_LINES)
        usable = [result for result in results if result.qualifies]
        chosen = max(usable, key=lambda result: result.early.rate, default=None)
        return PlaceLineStudy(results, chosen)

    def _line(self, tickets: pd.DataFrame, line: float) -> PlaceLineResult:
        bought = tickets[tickets["ev"] >= line]
        return PlaceLineResult(line, self._period(bought, EARLY_YEARS), self._period(bought, LATE_YEARS))

    def _period(self, bought: pd.DataFrame, years: tuple[int, int]) -> PaybackSummary:
        rows = bought[bought["year"].between(*years)]
        stake = pd.Series(100.0, index=rows.index)
        return self._payback.summarize(rows["day"], stake, rows["payout"])
