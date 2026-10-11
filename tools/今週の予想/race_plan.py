"""1レースの買う計画（参加の種類・買い目・金額）。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from 今週の予想.ticket_pick import TicketPick

#: 参加の種類の「買わない」。
NO_BET = "買わない"


@dataclass(frozen=True)
class PlacePick:
    """複勝1点。``horse_no`` は馬番、``probability`` は3着以内の確率、``value`` は複勝の期待値、``odds`` は最低オッズ、``yen`` は金額。"""

    horse_no: int
    probability: float | None
    value: float | None
    odds: float | None
    yen: int


@dataclass(frozen=True)
class RacePlan:
    """1レースの計画。``kind`` は 勝負／ノルマ（重賞）／ノルマ（日）／買わない、``reason`` はそう決めた理由（1文）、
    ``profit_units`` は見込みの利益 E（単位。Σ（期待値 − 1））、``max_value`` は最大の期待値 M、``graded`` は平地の重賞か、
    ``picks`` は買う複勝、``budget_yen`` はそのレースの予算。
    ``tickets`` は、それとは別に買う単勝・馬単（当日の期待度「高」のレース。参加の種類は「勝負（単勝・馬単）」）、``ticket_reason`` はその理由か、
    買わない理由（当日の期待度「高」なのに買わないときだけ）。複勝の参加の種類（``kind``）が「買わない」でも、単勝・馬単は買うことがある。"""

    rid: str
    title: str
    timing: str
    kind: str
    reason: str
    profit_units: float
    max_value: float | None
    graded: bool
    picks: tuple[PlacePick, ...] = ()
    budget_yen: int = 0
    tickets: tuple[TicketPick, ...] = ()
    ticket_reason: str = ""

    @property
    def place_yen(self) -> int:
        """複勝の金額（勝負用・ポリシー用の財布から出す）。"""
        return sum(pick.yen for pick in self.picks)

    @property
    def ticket_yen(self) -> int:
        """単勝・馬単の金額（単勝・馬単用の財布から出す）。"""
        return sum(ticket.yen for ticket in self.tickets)

    @property
    def stake_yen(self) -> int:
        """このレースで買う金額の合計。"""
        return self.place_yen + self.ticket_yen

    @property
    def buys(self) -> bool:
        """このレースで何か買うか。"""
        return self.stake_yen > 0

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "stake_yen": self.stake_yen, "place_yen": self.place_yen, "ticket_yen": self.ticket_yen}
