"""そのレースの「学ぶ帯」の大きさの材料。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .column_names import LOG_Q, ODDS, RACE_ID

REGION_Q, REGION_COUNT, REGION_HARVILLE = "reg_q", "reg_n", "reg_hv"
NAMES: tuple[str, ...] = (REGION_Q, REGION_COUNT, REGION_HARVILLE)


class RegionFeatures:
    """そのレースの組のうち、学ぶ下限以上のオッズの組がどれだけあるかを材料にする（レースの全部の組に同じ値）。

    - ``reg_q``: オッズが学ぶ下限以上（上限は見ない）の組の、市場の確率の合計。
    - ``reg_n``: オッズが学ぶ下限以上の組の数。例: 馬連の学ぶ下限が 8倍で、8倍以上の組が 60組なら 60。
    - ``reg_hv``: 対象の行（学ぶ下限以上・上限未満）の、予想の Harville の確率の合計（確率の出せなかった行は 0 として足す）。
    """

    def of(self, market: pd.DataFrame, learn_from: float, rows: pd.DataFrame, log_harville: pd.Series) -> pd.DataFrame:
        """``market`` はその券種の市場の表の全部の組、``rows`` はそのうちの対象の行、``log_harville`` は対象の行の ``log_hv``。"""
        at_or_above = market[market[ODDS] >= learn_from]
        by_race = np.exp(at_or_above[LOG_Q]).groupby(at_or_above[RACE_ID]).agg(["sum", "size"])
        harville = np.exp(log_harville).fillna(0.0)
        harville_sum = harville.groupby(rows[RACE_ID]).transform("sum")
        mapped = by_race.reindex(rows[RACE_ID])
        return pd.DataFrame({
            REGION_Q: mapped["sum"].to_numpy(dtype=float), REGION_COUNT: mapped["size"].to_numpy(dtype=float),
            REGION_HARVILLE: harville_sum.to_numpy(dtype=float),
        }, index=rows.index)
