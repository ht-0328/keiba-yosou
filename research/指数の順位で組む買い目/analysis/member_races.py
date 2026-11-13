"""表の1行の形（1つか複数）を、レースごとに合わせる。"""

from __future__ import annotations

import pandas as pd

from .payout_table import PAYOUT
from .row_spec import RowSpec
from .ticket_settlement import HIT, POINTS

#: 合わせた表の列。
COLUMNS: tuple[str, ...] = ("race_id", "race_date", POINTS, PAYOUT, HIT)


class MemberRaces:
    """精算の表（1行 = 1レース × 1つの形）から、``RowSpec`` の形の行を取り出し、レースごとに点数と払戻を足す。

    合計の行では、どれかの形が当たればそのレースは的中。買ったレース = 形のどれかに1点以上あるレース。
    """

    def of(self, settled: pd.DataFrame, spec: RowSpec) -> pd.DataFrame:
        rows = settled[settled["formation"].isin(spec.members)]
        if rows.empty:
            return pd.DataFrame(columns=list(COLUMNS))
        if not spec.is_total:
            return rows[list(COLUMNS)].reset_index(drop=True)
        merged = rows.groupby("race_id", as_index=False).agg(race_date=("race_date", "first"), **{POINTS: (POINTS, "sum"), PAYOUT: (PAYOUT, "sum")})
        merged[HIT] = merged[PAYOUT] > 0
        return merged[list(COLUMNS)]
