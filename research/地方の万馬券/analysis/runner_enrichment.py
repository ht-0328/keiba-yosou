"""出走の表を作る: 事実表を読み、調教師の地区・騎手の場内順位・人気の帯・事情を付ける。段1（事例）と段2（理論）が同じ表を使う。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import duckdb
import pandas as pd

from .jockey_venue_rank import JockeyVenueRank
from .popularity_band import PopularityBand
from .repository import FactsRepository, HorseAreaRepository, TrainerAreaRepository
from .runner_circumstances import RunnerCircumstances

#: 騎手の場内順位に前の年を使うので、始まりより 1年前から出走を読む。
_RANK_WARMUP = timedelta(days=366)


@dataclass(frozen=True)
class RunnerEnrichment:
    """``date_from`` 以降・``min_heads`` 頭以上の出走の行に、地区・場内順位・帯（``band``）・事情の列を付けて返す。"""

    con: duckdb.DuckDBPyConnection
    date_from: date
    min_heads: int
    popularity: PopularityBand = PopularityBand()

    def load(self) -> pd.DataFrame:
        rows = FactsRepository(self.con).load(self.date_from - _RANK_WARMUP)
        rows = rows.merge(TrainerAreaRepository(self.con).load(), on="trainer_code", how="left")
        rows = rows.merge(HorseAreaRepository(self.con).load(), on="horse_id", how="left")
        rows["trainer_area"] = rows["trainer_area"].fillna(rows["horse_area"])
        rows = JockeyVenueRank().attach(rows)
        in_scope = (pd.to_datetime(rows["race_date"]) >= pd.Timestamp(self.date_from)) & (rows["field_size"] >= self.min_heads)
        rows = rows[in_scope].reset_index(drop=True)
        rows = rows.assign(band=self.popularity.band_of(rows["popularity"]))
        return RunnerCircumstances().attach(rows)
