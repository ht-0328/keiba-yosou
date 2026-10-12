"""開催日を単位にしたブートストラップで、比の 90% の幅を出す。"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

#: 幅の下の端と上の端の分位（90% の幅）。
LOW, HIGH = 0.05, 0.95


class DayBootstrap:
    """開催日を同じ数だけ戻して引き直し（ブートストラップ）、引き直した日の合計から ``statistic`` を計算して、その分布の 90% の幅を返す。

    ``per_day`` は1行 = 1開催日の、数える量（投資・払戻・レース数など）の表。``statistic`` は列ごとの合計（Series）から比を返す関数。
    同じ日のレースは馬場や天気が同じで結果が似るので、レースではなく開催日を単位に引き直す（ほかの研究と同じ）。
    """

    def __init__(self, draws: int = 2000, seed: int = 42) -> None:
        self._draws = draws
        self._seed = seed

    def interval(self, per_day: pd.DataFrame, statistic: Callable[[pd.Series], float]) -> tuple[float, float]:
        if per_day.empty:
            return float("nan"), float("nan")
        values = per_day.to_numpy(dtype=float)
        rng = np.random.default_rng(self._seed)
        draws = rng.integers(0, len(values), size=(self._draws, len(values)))
        totals = values[draws].sum(axis=1)
        results = [statistic(pd.Series(total, index=per_day.columns)) for total in totals]
        low, high = np.nanquantile(results, [LOW, HIGH])
        return float(low), float(high)
