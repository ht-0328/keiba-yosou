"""係数の当てはめの流れ: 事実表の出走の行と全頭の予想の予測の表（backtest の pkl）、確定オッズから年ごとの票の表を組み、
1着・2着・3着の条件つきロジットを全部の年で当てはめる。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from .member_predictions import MemberPredictions
from .pool_tables import PoolTables
from .pool_tables_builder import PoolTablesBuilder
from .position_coefficients import PositionCoefficients
from .position_model import PositionModel
from .repository import FactsRowsRepository, LocalTicketOddsRepository, TrifectaOddsRepository

#: 票の見立てに使う券種（3連単は別のリポジトリ）。
_POOL_TICKETS: tuple[str, ...] = ("馬単", "3連複", "複勝")


@dataclass(frozen=True)
class FitSettings:
    """対象の最初の開催日・全頭の予想の予測の表の置き場所（当日の予測。対象の期間を全部含むもの）・最少の頭数。"""

    date_from: date
    predictions: Path
    min_heads: int = 11


class CoefficientFit:
    def __init__(self, con: duckdb.DuckDBPyConnection, settings: FitSettings) -> None:
        self._con = con
        self._settings = settings

    def run(self) -> tuple[PositionCoefficients, dict[str, Any]]:
        """係数と、当てはめの条件（置き場所の JSON に添える）。"""
        runners = self._runners()
        years = sorted(pd.to_datetime(runners["race_date"]).dt.year.unique())
        pools = [self._pools(runners[pd.to_datetime(runners["race_date"]).dt.year == year]) for year in years]
        coefficients = PositionModel().fit(pools)
        meta = {
            "当てはめた日": date.today().isoformat(), "対象の最初の開催日": self._settings.date_from.isoformat(),
            "最少の頭数": self._settings.min_heads, "年": [int(year) for year in years],
            "レース数": int(sum(len(tables.race_ids) for tables in pools)),
            "全頭の予想の予測": str(self._settings.predictions),
        }
        return coefficients, meta

    def _runners(self) -> pd.DataFrame:
        s = self._settings
        rows = FactsRowsRepository(self._con).load(s.date_from, s.min_heads)
        rows = rows.assign(race_id=rows["race_id"].astype(str))
        rows = rows.merge(MemberPredictions(s.predictions).load(), on=["race_id", "horse_no"], how="inner")
        if rows.empty:
            raise ValueError(f"事実表と予測の表（{s.predictions}）に共通のレースがありません")
        return rows.assign(race_id=rows["race_id"].astype("int64")).reset_index(drop=True)

    def _pools(self, horses: pd.DataFrame) -> PoolTables:
        ids = horses["race_id"].drop_duplicates()
        trifecta = TrifectaOddsRepository(self._con).load(ids)
        exacta, trio, place = (LocalTicketOddsRepository(self._con, ticket).load(ids) for ticket in _POOL_TICKETS)
        return PoolTablesBuilder().build(horses, trifecta, exacta, trio, place)
