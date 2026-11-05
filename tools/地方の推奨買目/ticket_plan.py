"""券種ごとの買い方: 期待値の線とオッズの範囲で、券種の組の表（確率・オッズ・払戻つき）から買う組を選ぶ。研究「地方の万馬券」の docs/05 で決めた。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .position_model import EV, PROBABILITY


@dataclass(frozen=True)
class TicketPlan:
    """1つの券種の買い方。``ev_min`` は期待値（直した確率 × 確定オッズ）の線、``odds_min``・``odds_max`` は組のオッズの範囲、
    ``min_heads`` はこの券種を買う最少の頭数（0 なら頭数を問わない）。"""

    ticket: str
    ev_min: float = 1.0
    odds_min: float = 0.0
    odds_max: float = float("inf")
    min_heads: int = 0

    def applies(self, heads: int) -> bool:
        """この頭数のレースで買うか。"""
        return heads >= self.min_heads

    @property
    def label(self) -> str:
        if self.odds_min <= 0 and np.isinf(self.odds_max):
            band = "全部"
        elif self.odds_min <= 0:
            band = f"〜{self.odds_max:g}倍"
        elif np.isinf(self.odds_max):
            band = f"{self.odds_min:g}倍〜"
        else:
            band = f"{self.odds_min:g}〜{self.odds_max:g}倍"
        return f"{band}・期待値 {self.ev_min:g} 以上"

    def choose(self, table: pd.DataFrame) -> pd.DataFrame:
        """``table`` は券種の組の表（``P``・``odds``・``payout``）。``odds`` が無く ``odds_lo``・``odds_hi``（複勝・ワイド）なら幅の真ん中を使う。"""
        if "odds" not in table.columns:
            table = table.assign(odds=(table["odds_lo"].astype(float) + table["odds_hi"].astype(float)) / 2.0)
        table = table.assign(**{EV: table[PROBABILITY] * table["odds"].astype(float)})
        chosen = table[(table[EV] >= self.ev_min) & (table["odds"] >= self.odds_min) & (table["odds"] <= self.odds_max)]
        return chosen.reset_index(drop=True)


#: 採った買い方（docs/05）。馬連・3連複は単体で 100% に届かないが、全券種をまとめた成績に含めて見る。
DEFAULT_PLANS: tuple[TicketPlan, ...] = (
    TicketPlan("単勝", 1.0, 0.0, 30.0),
    TicketPlan("複勝", 1.0, 0.0, 20.0),
    TicketPlan("枠連", 1.0),
    TicketPlan("ワイド", 1.0, 0.0, 50.0),
    TicketPlan("馬単", 1.05, 0.0, 50.0),
    TicketPlan("馬連", 1.0, 0.0, 20.0),
    TicketPlan("3連複", 1.0, 20.0, 300.0),
    TicketPlan("3連単", 1.05, 10.0, 200.0),
)
#: 本番の推奨買目の買い方（設計書「買うレースと買い目を決める」の 10）。未見の評価で 2024〜2026年とも回収率 100% を超えた 6券種
#: （馬連・3連複は入れない）。頭数の線は券種ごと: 単勝・枠連・ワイドは頭数を問わず、複勝・馬単・3連単は頭数が少ないレースで 100% を割るので線を置く。
RECOMMENDED_PLANS: tuple[TicketPlan, ...] = (
    TicketPlan("単勝", 1.0, 0.0, 30.0),
    TicketPlan("複勝", 1.0, 0.0, 20.0, min_heads=8),
    TicketPlan("枠連", 1.0),
    TicketPlan("ワイド", 1.0, 0.0, 50.0),
    TicketPlan("馬単", 1.05, 0.0, 50.0, min_heads=8),
    TicketPlan("3連単", 1.05, 10.0, 200.0, min_heads=8),
)
#: 比べる買い方（券種ごとに、オッズの帯 × 期待値の線）。
CANDIDATE_PLANS: tuple[TicketPlan, ...] = tuple(
    TicketPlan(ticket, ev_min, lo, hi)
    for ticket, bands in (
        ("単勝", ((0.0, np.inf), (0.0, 30.0))),
        ("複勝", ((0.0, np.inf), (0.0, 20.0))),
        ("枠連", ((0.0, np.inf), (0.0, 100.0))),
        ("ワイド", ((0.0, np.inf), (0.0, 50.0), (0.0, 10.0))),
        ("馬単", ((0.0, np.inf), (0.0, 50.0), (10.0, 200.0))),
        ("馬連", ((0.0, np.inf), (0.0, 20.0), (0.0, 50.0))),
        ("3連複", ((0.0, np.inf), (0.0, 30.0), (20.0, 300.0))),
        ("3連単", ((0.0, np.inf), (0.0, 100.0), (10.0, 200.0), (50.0, 200.0))),
    )
    for lo, hi in bands
    for ev_min in (1.0, 1.05, 1.1)
)
