"""これから走る1レースの、バイアスの補正の表を作る。"""

from __future__ import annotations

from collections.abc import Callable

import duckdb
import pandas as pd

from yosou.shared.dataset import OddsInput
from yosou.shared.feature import PredictionTiming

from . import names
from .bias_correction import BiasCorrection
from .day_slopes import DaySlopes
from .prior_slope_table import PriorSlopeTable
from .race_entry_repository import RaceEntryRepository
from .used_slopes import UsedSlopes

#: 展開の予測を返す関数の形（``DevelopmentPaceWorkflow.run`` と同じ）。
PaceForecast = Callable[[duckdb.DuckDBPyConnection, str, PredictionTiming, OddsInput | None], pd.DataFrame]


class RaceBiasSource:
    """1レースの出走馬（``RaceEntryRepository``）に、展開の予測④（``forecast``。保存した展開のモデル）の4コーナーの位置を付け、
    元DB の終わったレースの傾き（``slopes``。当日の先に終わったレースと前の日のレース）と過去の傾きの表（``table``）から
    使う傾きを出して、馬ごとのバイアスの補正にする（道具と、全頭の予想の予測の流れが使う）。

    ``slopes``・``table`` は ``PriorSlopeTableStore.load`` のもの（元DB が更新されていれば作り直したもの。その日の終わったレースも入っている）。
    """

    def __init__(self, forecast: PaceForecast, slopes: pd.DataFrame, table: PriorSlopeTable) -> None:
        self._forecast = forecast
        self._slopes = slopes
        self._table = table
        self._day = DaySlopes()
        self._used = UsedSlopes()
        self._correction = BiasCorrection()

    def of(self, con: duckdb.DuckDBPyConnection, race_id: str, timing: PredictionTiming,
           given_odds: OddsInput | None = None) -> pd.DataFrame:
        """1行 = 1頭。列は ``BiasCorrection.COLUMNS``。"""
        entries = RaceEntryRepository(con).read(race_id)
        forecasts = self._forecast(con, race_id, timing, given_odds)
        positions = forecasts[["horse_id", "corner4_pred"]].astype({"horse_id": str}).drop_duplicates("horse_id")
        entries = entries.merge(positions, on="horse_id", how="left")
        target = entries.iloc[[0]].reset_index(drop=True)
        day = self._day.of(target, self._slopes, timing)
        used = self._used.of(day, self._table.lookup(target)).set_axis([race_id])
        return self._correction.of(entries, used)

    def used_slopes(self, con: duckdb.DuckDBPyConnection, race_id: str, timing: PredictionTiming) -> pd.DataFrame:
        """そのレースの、当日の傾き・レース数・過去の傾き・使う傾き（1行。道具で見せる用）。"""
        target = RaceEntryRepository(con).read(race_id).iloc[[0]].reset_index(drop=True)
        day = self._day.of(target, self._slopes, timing)
        prior = self._table.lookup(target)
        return pd.concat([target[[names.RACE_ID, names.CONDITION_CODE, names.MEETING_DAY]], day, prior, self._used.of(day, prior)], axis=1)
