"""1回の WIN5 の買い目を精算した結果。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Win5Settled:
    """``stake`` は代金（円）、``payout`` は払戻（当たりの払戻と、返還の代金の合計。円）、``hit`` は買い目のどれかが当たったか、
    ``refunded_points`` は返還になった点数（取消・除外の馬を含む組）。"""

    points: int
    stake: int
    payout: int
    hit: bool
    refunded_points: int
