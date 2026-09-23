"""回収率のまとめ。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..settlement.settlement_table import HIT_COUNT, PAYOUT_YEN, POINTS, STAKE_YEN


@dataclass(frozen=True)
class ReturnSummary:
    """精算表の行の集まり（1つの買い方 × 選んだレース）からの、回収率のまとめ。

    - ``races``: 対象にしたレース数（見送りも含む）。``bet_races``: 買ったレース数。
    - ``points``・``stake_yen``・``payout_yen``: 点数・賭け金・払戻の合計。
    - ``hit_races``: 1点でも当たったレース数。``max_race_payout``: 1レースの払戻の最大。
    回収率 = 払戻 ÷ 賭け金。最大を除く回収率は、最大の1レースの払戻を除いた回収率（1レースの大当たりに頼っていないかを見る）。
    """

    races: int
    bet_races: int
    points: int
    stake_yen: int
    payout_yen: int
    hit_races: int
    max_race_payout: int

    @classmethod
    def from_rows(cls, rows: pd.DataFrame) -> ReturnSummary:
        """精算表の行（``SettlementTable`` の列）から作る。"""
        bet = rows[rows[POINTS] > 0]
        return cls(
            races=len(rows), bet_races=len(bet), points=int(bet[POINTS].sum()), stake_yen=int(bet[STAKE_YEN].sum()),
            payout_yen=int(bet[PAYOUT_YEN].sum()), hit_races=int((bet[HIT_COUNT] > 0).sum()),
            max_race_payout=int(bet[PAYOUT_YEN].max()) if len(bet) else 0,
        )

    @property
    def return_rate(self) -> float | None:
        """回収率（1.0 で元返し）。買っていなければ None。"""
        return self.payout_yen / self.stake_yen if self.stake_yen else None

    @property
    def hit_race_rate(self) -> float | None:
        return self.hit_races / self.bet_races if self.bet_races else None

    @property
    def return_rate_without_max(self) -> float | None:
        """最大の1レースの払戻を除いた回収率。"""
        return (self.payout_yen - self.max_race_payout) / self.stake_yen if self.stake_yen else None

    def __add__(self, other: ReturnSummary) -> ReturnSummary:
        """2つのまとめを足す（広めと少点数を合わせるとき）。レース数は重なることがあるので、呼ぶ側が意味を決める。"""
        return ReturnSummary(
            self.races + other.races, self.bet_races + other.bet_races, self.points + other.points,
            self.stake_yen + other.stake_yen, self.payout_yen + other.payout_yen, self.hit_races + other.hit_races,
            max(self.max_race_payout, other.max_race_payout),
        )
