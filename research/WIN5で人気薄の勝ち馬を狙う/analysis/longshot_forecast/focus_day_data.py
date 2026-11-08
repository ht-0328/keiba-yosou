"""詳しく見る日（例 2026-11-08）の対象レースの、人気薄の1着の予想に渡すデータを、今のモデルの予測の流れから作る。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import duckdb
import numpy as np
import pandas as pd

from yosou.shared.dataset.column_names import WIN_ODDS as MARKET_WIN_ODDS
from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.odds import MarketWinProbability
from yosou.shared.workflow import FormAptitudePrediction

from .longshot_data import HORSE_ID, HORSE_NO, RACE_DATE, RACE_ID, LongshotData
from .type_features import COLUMNS as TYPE_COLUMNS


@dataclass(frozen=True)
class FocusDayData:
    """``prediction`` は今のモデルの予測の流れ（WIN5 の予想と同じ組み立て）。1着のモデルの予測用データ（今のモデルの1着の材料・基準）に、
    型の材料を足し、学習の列（``columns``）にそろえる。人気は締め切り前の単勝オッズ（元DB にある最新）の順。"""

    prediction: FormAptitudePrediction
    type_features: pd.DataFrame
    columns: Sequence[str]
    categorical: tuple[str, ...]

    def build(self, con: duckdb.DuckDBPyConnection, race_ids: Sequence[str], timing: PredictionTiming) -> tuple[LongshotData, pd.DataFrame]:
        """（全頭の予測用データ, 今のモデルの1着の確率の表）。"""
        workflow = self.prediction.workflow(con, timing)
        parts = [self._race(workflow, race_id, timing) for race_id in race_ids]
        data = LongshotData(*(pd.concat([getattr(part, name) for part, _ in parts], ignore_index=True)
                              for name in ("ids", "features", "label", "baseline", "popularity", "market")), self.categorical)
        current = pd.concat([table for _, table in parts], ignore_index=True)
        return data, current

    def _race(self, workflow, race_id: str, timing: PredictionTiming) -> tuple[LongshotData, pd.DataFrame]:
        win = workflow.win_data(race_id, timing)
        table = workflow.run(race_id, timing)
        ids = win.ids.reset_index(drop=True).astype({RACE_ID: str})
        odds = win.market[MARKET_WIN_ODDS].reset_index(drop=True).astype(float)
        keys = ids[[RACE_ID, HORSE_NO]].astype({HORSE_NO: int})
        added = keys.merge(self.type_features, on=[RACE_ID, HORSE_NO], how="left")[list(TYPE_COLUMNS)]
        features = pd.concat([win.features.reset_index(drop=True), added], axis=1)
        features = features.reindex(columns=list(self.columns))
        market = MarketWinProbability().of(ids[RACE_ID], odds).reset_index(drop=True)
        data = LongshotData(ids[[RACE_ID, RACE_DATE, HORSE_ID, HORSE_NO]], features, pd.Series(np.zeros(len(ids), dtype=int)),
                            win.baseline.values.reset_index(drop=True), odds.rank(method="first"), market, self.categorical)
        return data, table
