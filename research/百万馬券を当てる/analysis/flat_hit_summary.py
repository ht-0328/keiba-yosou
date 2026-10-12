"""第3段: 一律の買い方の、1,000倍以上で決まったレースのうち当てた割合を数える（docs/06 の 3）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import RACE_ID

from .obi_rules import BIG_YEN
from .race_table_loader import TRIFECTA_YEN
from .ticket_settler import HIT


class FlatHitSummary:
    """精算した買い目（1行 = 1点）と選んだレースの表から、買ったレースのうち 1,000倍以上で決まったレースの数と、
    そのうち当てたレースの数・割合を1行の辞書にする。

    一律の買い方は 1,000倍以上の組しか買わないので、当てられるのは 1,000倍以上で決まったレースだけ。
    組の順位の付け方の良さは、この割合で比べる（回収率は数回の大きい当たりで動くため）。
    """

    def row(self, settled: pd.DataFrame, races: pd.DataFrame) -> dict[str, object]:
        bought = set(settled[RACE_ID])
        wild = races[races[RACE_ID].isin(bought) & races[TRIFECTA_YEN].ge(BIG_YEN)]
        hit_races = set(settled.loc[settled[HIT], RACE_ID])
        hits = int(wild[RACE_ID].isin(hit_races).sum())
        return {"買ったレース": len(bought), "1,000倍以上で決まったレース": len(wild), "うち当てたレース": hits,
                "当てた割合": round(hits / len(wild), 3) if len(wild) else float("nan")}
