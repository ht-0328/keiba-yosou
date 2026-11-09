"""買い目に払戻を当てて、レースごとの点数・払戻・的中にまとめる。"""

from __future__ import annotations

import pandas as pd

from .payout_table import PAYOUT
from .ticket_builder import COMBO

POINTS, HIT = "points", "hit"
#: 精算の表の列（1行 = 1レース）。``payout`` は 1点 100円で買ったときの払戻の合計（円）。
COLUMNS: tuple[str, ...] = ("race_id", POINTS, PAYOUT, HIT)


class TicketSettlement:
    """買い目の表（``TicketBuilder.build``）と払戻の表（``PayoutTable.read``）を（レースID, 組の数）で突き合わせ、
    レースごとに 点数・払戻（1点 100円）・的中したか にまとめる。払戻の無い組は外れ（0円）。
    """

    def settle(self, tickets: pd.DataFrame, payouts: pd.DataFrame) -> pd.DataFrame:
        if tickets.empty:
            return pd.DataFrame(columns=list(COLUMNS))
        merged = tickets.merge(payouts, on=["race_id", COMBO], how="left")
        merged[PAYOUT] = merged[PAYOUT].fillna(0.0).astype(float)
        per_race = merged.groupby("race_id", as_index=False).agg(**{POINTS: (COMBO, "size"), PAYOUT: (PAYOUT, "sum")})
        per_race[HIT] = per_race[PAYOUT] > 0
        return per_race[list(COLUMNS)]
