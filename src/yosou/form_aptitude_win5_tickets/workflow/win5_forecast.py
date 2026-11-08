"""WIN5 の日の予測の結果。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..formation import DayDecision, FormationChoice, LegOrdering
from ..payout import PayoutPool
from ..repository import Win5Day
from .leg_forecast import LegForecast


@dataclass(frozen=True)
class Win5Forecast:
    """WIN5 の日（``Win5Day``）・対象レースごとの予測（``LegForecast``）・払戻に回るお金の見込み（``PayoutPool``）・
    並べ方・予算・買う日の線・選んだ買い目（``FormationChoice``）・予算の候補ごとのいちばん良い買い目・買うか見送りか・
    配当の見積もりの式に使った当たり組の数・予想した時刻。"""

    day: Win5Day
    legs: tuple[LegForecast, ...]
    pool: PayoutPool
    ordering: LegOrdering
    budget: int
    line: float
    choice: FormationChoice
    by_budget: dict[int, FormationChoice]
    decision: DayDecision
    estimator_count: int
    made_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """記録（``Win5ForecastRecordRepository``）の形。"""
        picks = self.choice.formation.legs
        return {
            "開催日": self.day.race_date.isoformat(), "予想した時刻": self.made_at.isoformat(timespec="seconds"),
            "キャリーオーバー": self.day.carry, "発売票数の見積もり": self.pool.votes, "並べ方": self.ordering.label,
            "予算": self.budget, "買う日の線": self.line, "判断": self.decision.label, **self.choice.to_dict(),
            "配当の見積もりの式に使った当たり組の数": self.estimator_count,
            "対象レース": [leg.to_dict(leg_picks) for leg, leg_picks in zip(self.legs, picks, strict=True)],
            "予算の候補": [{"予算": budget, **choice.to_dict()} for budget, choice in sorted(self.by_budget.items())],
        }
