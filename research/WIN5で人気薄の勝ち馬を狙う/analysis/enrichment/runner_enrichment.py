"""出走の表を作る流れ: 事実表の行に、過去走・人・血統・市場・結果側・今のモデルの列を順に足し、WIN5 の対象レースの印を付ける。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from .model_uplift import ModelUplift
from .people_rates import PeopleRates
from .race_market_shape import RaceMarketShape
from .race_outcome_side import RaceOutcomeSide
from .runner_history import RunnerHistory
from .sire_going_rates import SireGoingRates

_JUMP = "障害"


@dataclass(frozen=True)
class RunnerEnrichment:
    """``runners`` は事実表の行（障害も含め、過去走をたどれるよう ``date_from`` より前の年から）。返すのは ``date_from`` 以降の平地の行で、
    ``win5_leg``（WIN5 の何レース目か。対象でなければ欠損値）の列が付く。"""

    predictions: tuple[pd.DataFrame, ...]
    date_from: date

    def build(self, runners: pd.DataFrame, legs: pd.DataFrame) -> pd.DataFrame:
        frame = RunnerHistory().add(runners)
        frame = PeopleRates().add(frame)
        frame = SireGoingRates().add(frame)
        frame = frame.loc[(frame["surface"] != _JUMP) & (frame["race_date"] >= self.date_from.isoformat())]
        frame = RaceMarketShape().add(frame)
        frame = RaceOutcomeSide().add(frame)
        frame = ModelUplift(self.predictions).add(frame)
        leg_of = legs.drop_duplicates("race_id").set_index("race_id")["leg"]
        frame["win5_leg"] = frame["race_id"].map(leg_of)
        return frame.sort_values(["race_id", "horse_no"]).reset_index(drop=True)
