"""提案に書く運用の数値（どのレースを・複勝で・1レース何円・何点）。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import columns as c

_RACE_KEY = [c.WINDOW, c.PART, c.RACE_ID]


@dataclass(frozen=True)
class OperationalSummary:
    """買った買い目から出す、運用の目安。

    - ``days``・``races``・``points``: 買った開催日数・レース数・点数。
    - ``races_per_day_mean``・``races_per_day_max``: 1開催日に買ったレース数の平均と最大（買った日だけ）。
    - ``points_per_race_mean``: 1レースの点数の平均。``yen_per_race_mean``: 1レースの賭け金の平均（1点 100円のとき）。
    - ``yen_per_day_mean``・``yen_per_month_mean``: 1開催日・1か月の賭け金の平均。
    - ``graded_races``: そのうち平地の重賞のレース数。
    """

    days: int
    races: int
    points: int
    races_per_day_mean: float
    races_per_day_max: int
    points_per_race_mean: float
    yen_per_race_mean: float
    yen_per_day_mean: float
    yen_per_month_mean: float
    graded_races: int

    @classmethod
    def of(cls, tickets: pd.DataFrame, races: pd.DataFrame) -> OperationalSummary:
        if tickets.empty:
            return cls(0, 0, 0, np.nan, 0, np.nan, np.nan, np.nan, np.nan, 0)
        per_race = tickets.groupby(_RACE_KEY).agg(points=(c.STAKE_YEN, "size"), stake=(c.STAKE_YEN, "sum"),
                                                  day=(c.RACE_DATE, "first")).reset_index()
        per_day = per_race.groupby("day").agg(races=("stake", "size"), stake=("stake", "sum"))
        per_month = per_race.groupby(per_race["day"].dt.to_period("M"))["stake"].sum()
        graded = races.loc[races[c.IS_GRADED].fillna(False).astype(bool), _RACE_KEY]
        graded_count = len(per_race.merge(graded, on=_RACE_KEY, how="inner"))
        return cls(
            days=len(per_day), races=len(per_race), points=len(tickets),
            races_per_day_mean=float(per_day["races"].mean()), races_per_day_max=int(per_day["races"].max()),
            points_per_race_mean=float(per_race["points"].mean()), yen_per_race_mean=float(per_race["stake"].mean()),
            yen_per_day_mean=float(per_day["stake"].mean()), yen_per_month_mean=float(per_month.mean()), graded_races=graded_count,
        )
