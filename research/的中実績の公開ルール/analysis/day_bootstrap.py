"""開催日を引き直して、運が悪いほうに振れたときの回収率を出す。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 引き直す回数。
_DRAWS = 4000
#: 「運が悪いほう」の端（下から 5%）。
LOW_PERCENTILE = 5.0


class DayBootstrap:
    """買った行（列 ``day``・``win_pay``。1行 = 100円）を開催日ごとにまとめ、開催日を引き直して回収率を ``_DRAWS`` 回出し、下から ``LOW_PERCENTILE`` % の値を返す。
    同じ日のレースは同じ馬場・同じ流れになりやすいので、レースでなく開催日を単位に引き直す。"""

    def __init__(self, seed: int = 1) -> None:
        self._seed = seed

    def low(self, bought: pd.DataFrame) -> float:
        if bought.empty:
            return float("nan")
        days = bought.groupby("day")["win_pay"].agg(["sum", "size"])
        draws = np.random.default_rng(self._seed).integers(0, len(days), (_DRAWS, len(days)))
        returns = days["sum"].to_numpy()[draws].sum(axis=1) / days["size"].to_numpy()[draws].sum(axis=1)
        return float(np.percentile(returns, LOW_PERCENTILE))
