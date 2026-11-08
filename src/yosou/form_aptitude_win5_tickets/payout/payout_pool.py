"""その日の WIN5 の、払戻に回るお金の見込みを表す値。"""

from __future__ import annotations

from dataclasses import dataclass

from .win5_rules import PAYOUT_RATE, TICKET_YEN


@dataclass(frozen=True)
class PayoutPool:
    """発売票数の見積もり（``PoolSizeEstimate``）と、キャリーオーバー金額初期（円）。"""

    votes: float
    carry: int

    @property
    def sales_share(self) -> float:
        """売上のうち払戻に回るお金（円）= 発売票数の見積もり × 100円 × 払戻率。"""
        return self.votes * TICKET_YEN * PAYOUT_RATE

    @property
    def money(self) -> float:
        """払戻に回るお金（円）= 売上の払戻に回る分 + キャリーオーバー。"""
        return self.sales_share + self.carry
