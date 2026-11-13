"""WIN5 の日の予測の結果。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..formation import BudgetTiers, DayDecision, FormationChoice, LegOrdering
from ..payout import PayoutPool
from ..repository import Win5Day
from .leg_forecast import LegForecast


@dataclass(frozen=True)
class Win5Forecast:
    """WIN5 の日（``Win5Day``）・対象レースごとの予測（``LegForecast``）・払戻に回るお金の見込み（``PayoutPool``）・並べ方・
    段階の予算（``BudgetTiers``）・買う日の線・判断用の買い目（``judge``。この日の期待値で買うか見送りかを決めた）・本命の確率の積・
    買う買い目（``choice``。多く買う日は多く買う日の予算、少なく買う日と見送りの日は少なく買う日の予算の買い目）・予算の候補ごとの
    いちばん良い買い目・判断（買う（多く）・買う（少なく）・見送り）・配当の見積もりの式に使った当たり組の数・予想した時刻。"""

    day: Win5Day
    legs: tuple[LegForecast, ...]
    pool: PayoutPool
    ordering: LegOrdering
    tiers: BudgetTiers
    line: float
    judge: FormationChoice
    favorite_product: float
    choice: FormationChoice
    by_budget: dict[int, FormationChoice]
    decision: DayDecision
    estimator_count: int
    made_at: datetime

    @property
    def budget(self) -> int:
        """買う買い目の予算（点）。"""
        return self.tiers.budget_for(self.decision)

    def to_dict(self) -> dict[str, Any]:
        """記録（``Win5ForecastRecordRepository``）の形。「予算」「買い目」「点数」「代金」「当たる確率」「日の期待値」は買う買い目のもの
        （段階の予算の前の記録と同じ鍵）。判断用の買い目の値は「判断用の…」、段階の予算は ``BudgetTiers.to_dict()`` の鍵で足す。"""
        picks = self.choice.formation.legs
        return {
            "開催日": self.day.race_date.isoformat(), "予想した時刻": self.made_at.isoformat(timespec="seconds"),
            "キャリーオーバー": self.day.carry, "発売票数の見積もり": self.pool.votes, "並べ方": self.ordering.label,
            **self.tiers.to_dict(), "買う日の線": self.line,
            "判断用の点数": self.judge.formation.points, "判断用の当たる確率": self.judge.hit_probability,
            "判断用の期待値": self.judge.expected_value, "本命の確率の積": self.favorite_product,
            "判断": self.decision.label, "段階": self.decision.tier_label, "予算": self.budget, **self.choice.to_dict(),
            "配当の見積もりの式に使った当たり組の数": self.estimator_count,
            "対象レース": [leg.to_dict(leg_picks) for leg, leg_picks in zip(self.legs, picks, strict=True)],
            "予算の候補": [{"予算": budget, **choice.to_dict()} for budget, choice in sorted(self.by_budget.items())],
        }
