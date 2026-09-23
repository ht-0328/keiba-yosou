"""券種ごとの買い方1つ。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 馬券の買い方の検証.analysis.ticket import TicketType

#: 買い目の候補の表の列の名前（``RaceCandidateBuilder`` が作る）。
RACE, TICKET, COMBO = "レースID", "券種", "組番"
PROBABILITY, ODDS, PRICE, VALUE = "当たる確率", "確定オッズ", "見込みの倍率", "期待値"


@dataclass(frozen=True)
class BettingRule:
    """券種ごとの買い方: 「期待値が ``min_value`` 以上で、オッズが ``max_odds`` 以下の買い目を、
    1レースにつき期待値の高い順に ``per_race`` 点まで買う」。

    例: 3連複で (1.2, 300, 3) なら、期待値 1.2 以上・300倍以下の組み合わせを、1レース3点まで買う。
    オッズは複勝・ワイドでは最低オッズ。1点 100円。
    """

    ticket_type: TicketType
    min_value: float
    max_odds: float
    per_race: int

    def select(self, candidates: pd.DataFrame) -> pd.DataFrame:
        """``candidates``（その券種の候補）から、この買い方で買う買い目。"""
        passing = candidates[(candidates[VALUE] >= self.min_value) & (candidates[ODDS] <= self.max_odds)]
        ranked = passing.sort_values([RACE, VALUE], ascending=[True, False], kind="stable")
        return ranked[ranked.groupby(RACE).cumcount() < self.per_race]

    def describe(self) -> str:
        """表に出す書き方。"""
        return f"期待値 {self.min_value:g} 以上・{self.max_odds:g}倍以下・1レース {self.per_race}点まで"
