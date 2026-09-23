"""1レース × 1買い方の結果。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanResult:
    """1レースに1つの買い方を当てた結果。見送ったときは ``skipped`` に理由が入り、点数・賭け金・払戻は 0。"""

    race_id: str
    plan_name: str
    points: int
    stake_yen: int
    payout_yen: int
    hit_count: int
    skipped: str | None = None

    @classmethod
    def skip(cls, race_id: str, plan_name: str, reason: str) -> PlanResult:
        return cls(race_id, plan_name, 0, 0, 0, 0, reason)

    @property
    def is_bet(self) -> bool:
        """買ったか（見送りでなく、点数がある）。"""
        return self.points > 0
