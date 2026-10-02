"""前半・後半の組の予測を、ほかの予想に渡す元の予測の表（まとまり P の元）にする。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID
from yosou.shared.feature.pace_forecast import pace_forecast_columns as names

from .group_forecast import (
    BACK_PROBABILITY,
    CLOSING_PREDICTION,
    CORNER4_PREDICTION,
    FIRST_HALF_QUANTILES,
    FRONT_PROBABILITY,
    HIGH_PROBABILITY,
    LEADER_PROBABILITY,
    MIDDLE_PROBABILITY,
    SECOND_HALF_QUANTILES,
    SLOW_PROBABILITY,
    GroupForecast,
)

#: この予想の予測の列 → まとまり P の元の予測の列（1頭ごと）。
_EARLY_HORSE = {LEADER_PROBABILITY: names.LEADER, FRONT_PROBABILITY: names.FRONT,
                MIDDLE_PROBABILITY: names.MIDDLE, BACK_PROBABILITY: names.BACK}
_LATE_HORSE = {CORNER4_PREDICTION: names.CORNER4, CLOSING_PREDICTION: names.CLOSING}
#: この予想の予測の列 → まとまり P の元の予測の列（1レースごと。同じレースの馬に配る）。
_EARLY_RACE = {SLOW_PROBABILITY: names.SLOW, HIGH_PROBABILITY: names.HIGH, FIRST_HALF_QUANTILES[0]: names.FIRST_LOW,
               FIRST_HALF_QUANTILES[1]: names.FIRST_MIDDLE, FIRST_HALF_QUANTILES[2]: names.FIRST_HIGH}
_LATE_RACE = {SECOND_HALF_QUANTILES[1]: names.SECOND_MIDDLE}


class PaceSourceTable:
    """前半の組と後半の組の予測を、1行 = 1頭の表（列 ``race_id``・``horse_id`` と ``pace_forecast.SOURCE_COLUMNS``）にする。

    近走と適性の予想が、展開の予想の結果（まとまり P）を作るのに使う（共通の ``PaceForecastTableBuilder`` に渡す）。
    行は前半の組の馬。後半の予測が無い馬（後半の予測が始まる前の年など）は、後半の列が欠損値。
    """

    def of(self, early: GroupForecast, late: GroupForecast) -> pd.DataFrame:
        ids = early.horses[[RACE_ID, HORSE_ID]].astype(str).drop_duplicates().reset_index(drop=True)
        parts = [early.horse_rows(ids).rename(columns=_EARLY_HORSE), early.race_rows(ids).rename(columns=_EARLY_RACE),
                 late.horse_rows(ids).rename(columns=_LATE_HORSE), late.race_rows(ids).rename(columns=_LATE_RACE)]
        table = pd.concat([ids.rename(columns={RACE_ID: "race_id", HORSE_ID: "horse_id"}), *parts], axis=1)
        return table.reindex(columns=[*names.KEY, *names.SOURCE_COLUMNS])
