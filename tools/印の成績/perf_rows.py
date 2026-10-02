"""出走の行（DataFrame）から成績7つの1行を作る。"""

from __future__ import annotations

import pandas as pd

from 共通.perf import PerfRow


def perf_row_of(rows: pd.DataFrame, label: str = "") -> PerfRow:
    """列 finish・win_payout・place_payout の行から、成績7つ（``共通.perf.PerfRow``）を作る。着順の付かない馬は着外。"""
    finish = rows["finish"]
    return PerfRow((label,), len(rows), int((finish == 1).sum()), int((finish == 2).sum()), int((finish == 3).sum()),
                   int(rows["win_payout"].sum()), int(rows["place_payout"].sum()))
