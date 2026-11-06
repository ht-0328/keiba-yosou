"""券種ごとの買い方: 期待値の線とオッズの範囲（と 頭数・組の形・荒れ具合・点数の上限）で、券種の組の表（確率・オッズ・払戻つき）から買う組を選ぶ。
研究「地方の万馬券」の docs/05・06 で決めた。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .combo_forms import FORM
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
    #: 組の形（人気の帯を 人・中・大 の順に並べた文字。例 ``人中`` は 人気馬 × 中穴。空なら形を問わない。``|`` で複数）。
    form: str = ""
    #: 1レースの点数の上限（期待値の高い順に残す。0 なら上限なし）。
    top_k: int = 0
    #: 荒れ具合の条件: その券種の「中荒れ以上の確率」（地方の荒れ具合の予想 ``yosou.local_upset_level``）がこの値以上のレースだけ買う（0 なら問わない）。
    upset_min: float = 0.0

    def applies(self, heads: int) -> bool:
        """この頭数のレースで買うか。"""
        return heads >= self.min_heads

    def allows_upset(self, upset: float | None) -> bool:
        """この荒れ具合（中荒れ以上の確率）のレースで買うか。条件が無ければ常に買う。条件があるのに値が無ければ買わない。"""
        if self.upset_min <= 0:
            return True
        return upset is not None and upset >= self.upset_min

    @property
    def forms(self) -> tuple[str, ...]:
        return tuple(part for part in self.form.split("|") if part)

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
        parts = [band, f"期待値 {self.ev_min:g} 以上"]
        if self.form:
            parts.append(f"型 {'・'.join(self.forms)}")
        if self.upset_min > 0:
            parts.append(f"中荒れ以上の確率 {self.upset_min:g} 以上")
        if self.top_k:
            parts.append(f"期待値の上位 {self.top_k} 点")
        return "・".join(parts)

    def choose(self, table: pd.DataFrame) -> pd.DataFrame:
        """``table`` は券種の組の表（``P``・``odds``・``payout``）。``odds`` が無く ``odds_lo``・``odds_hi``（複勝・ワイド）なら幅の真ん中を使う。
        形を問う買い方は ``form`` の列（``ComboForms`` が付ける）で絞る。点数の上限があれば、期待値の高い順に残す。
        荒れ具合の条件は、組の表でなくレースの値なので、呼ぶ側が ``allows_upset`` で先に見る。"""
        if "odds" not in table.columns:
            table = table.assign(odds=(table["odds_lo"].astype(float) + table["odds_hi"].astype(float)) / 2.0)
        table = table.assign(**{EV: table[PROBABILITY] * table["odds"].astype(float)})
        chosen = table[(table[EV] >= self.ev_min) & (table["odds"] >= self.odds_min) & (table["odds"] <= self.odds_max)]
        if self.form:
            chosen = chosen[chosen[FORM].isin(self.forms)]
        if self.top_k:
            chosen = chosen.sort_values(EV, ascending=False, kind="stable").head(self.top_k)
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
#: 本番の推奨買目の買い方（設計書「買うレースと買い目を決める」の 10）。未見の評価で 2024〜2026年とも回収率 100% を超えた買い方だけ。
#: 頭数の線は券種ごと: 単勝・枠連・ワイドは頭数を問わず、複勝・馬単・3連単・3連複は頭数が少ないレースで 100% を割るので線を置く。
#: 馬連は 人気馬（1〜3番人気）× 中穴（4〜7番人気）の組だけ、3連複は 3連複の中荒れ以上の確率 0.6 以上のレースで期待値の上位 3点だけ
#: （研究「地方の万馬券」の docs/06）。
RECOMMENDED_PLANS: tuple[TicketPlan, ...] = (
    TicketPlan("単勝", 1.0, 0.0, 30.0),
    TicketPlan("複勝", 1.0, 0.0, 20.0, min_heads=8),
    TicketPlan("枠連", 1.0),
    TicketPlan("馬連", 1.0, 0.0, 20.0, min_heads=11, form="人中"),
    TicketPlan("ワイド", 1.0, 0.0, 50.0),
    TicketPlan("馬単", 1.05, 0.0, 50.0, min_heads=8),
    TicketPlan("3連複", 1.0, 10.0, 100.0, min_heads=8, top_k=3, upset_min=0.6),
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
