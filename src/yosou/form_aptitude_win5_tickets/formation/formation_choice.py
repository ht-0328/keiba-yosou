"""組んだフォーメーションと、その当たる確率・日の期待値。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..payout import TICKET_YEN
from .formation import Formation


@dataclass(frozen=True)
class FormationChoice:
    """``hit_probability`` は買い目のどれかが当たる確率（組の当たる確率の合計）、``expected_payout`` は見積もりの払戻の合計
    （全部の組の「当たる確率 × 見積もりの配当」の合計。円）。"""

    formation: Formation
    hit_probability: float
    expected_payout: float

    @property
    def stake(self) -> int:
        """代金（円）= 点数 × 100円。"""
        return self.formation.points * TICKET_YEN

    @property
    def expected_value(self) -> float:
        """日の期待値 = 見積もりの払戻の合計 ÷ 代金（1 で元返し）。"""
        return self.expected_payout / self.stake

    def to_dict(self) -> dict[str, Any]:
        return {
            "買い目": [list(picks) for picks in self.formation.legs], "点数": self.formation.points, "代金": self.stake,
            "当たる確率": self.hit_probability, "見積もりの払戻の合計": self.expected_payout, "日の期待値": self.expected_value,
        }
