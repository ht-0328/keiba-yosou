"""これから走る1レースの出走馬の、前らしさの見込みを返す（``RaceBiasSource`` の ``forecast`` の地方版）。"""

from __future__ import annotations

import duckdb
import pandas as pd

from yosou.shared.dataset import OddsInput
from yosou.shared.feature import PredictionTiming
from yosou.track_bias import RaceEntryRepository, names

from .front_position import FRONT_POSITION
from .repository import PastPositionRepository


class LocalFrontForecast:
    """展開の予想の代わりに、出走馬の直近3走の4コーナーの位置の平均（``PastPositionRepository``）を、
    ``RaceBiasSource`` が読む形（1行 = 1頭。``horse_id``・``corner4_pred``）で返す。時点と渡されたオッズは使わない。"""

    def run(self, con: duckdb.DuckDBPyConnection, race_id: str, timing: PredictionTiming,
            given_odds: OddsInput | None = None) -> pd.DataFrame:
        entries = RaceEntryRepository(con).read(race_id)
        race_day = pd.Timestamp(entries[names.RACE_DATE].iloc[0]).date()
        positions = PastPositionRepository(con).read(race_day, entries["horse_id"].astype(str).tolist())
        return entries[["horse_id"]].astype(str).merge(positions, on="horse_id", how="left").reindex(columns=["horse_id", FRONT_POSITION])
