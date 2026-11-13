"""今のモデルに足す材料の表を、元DB とほかの置き場所から時点ごとに作って reports/ に書き、読む。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from yosou.shared.feature import PredictionTiming

from ..enrichment.runner_enrichment import RunnerEnrichment, SideTables
from ..repository import PaceForecastStore, RaceReviewRepository, RunnerFactsRepository
from ..repository.pace_forecast_store import DEFAULT_PACE_FORECASTS
from ..repository.race_review_repository import DEFAULT_REVIEW_DB
from .prior_race_bias import DEFAULT_SLOPES, PriorRaceBias
from .scenario_materials import ScenarioMaterials

#: 展開の予想の年ごとの予測の置き場所（時点ごと。前日・当日のフォルダが並ぶ）。
_FORECAST_ROOT = DEFAULT_PACE_FORECASTS.parent
_FORECAST_FOLDER = {PredictionTiming.DAY_BEFORE: "day_before", PredictionTiming.RACE_DAY: "race_day"}
_FORECAST_COLUMNS = ("p_slow", "p_even", "p_high", "p_leader", "p_front", "p_middle", "p_back")


@dataclass(frozen=True)
class ScenarioMaterialSource:
    """``root`` に ``材料-<時点>.pkl`` を書く（1行 = 1頭。race_id・horse_no と ``ScenarioMaterials`` の列）。
    学習の表（今のモデルの学習の表）が 2012年からなので、2012年から作る。過去走（斤量・位置の近走）は 2011年から読む。"""

    root: Path
    date_from: date = date(2012, 1, 1)
    history_from: date = date(2011, 1, 1)
    review_db: Path = DEFAULT_REVIEW_DB
    slopes: Path = DEFAULT_SLOPES

    def build(self, con: duckdb.DuckDBPyConnection) -> list[Path]:
        history = RunnerFactsRepository(con).load(self.history_from)
        empty = pd.DataFrame(columns=["race_id", "horse_no", "pre_close_odds", "pre_close_popularity"])
        side = SideTables(reviews=RaceReviewRepository(self.review_db).load(), race_forecasts=self._empty(["race_id"], _FORECAST_COLUMNS[:3]),
                          horse_forecasts=self._empty(["race_id", "horse_id"], _FORECAST_COLUMNS[3:]), pre_close=empty)
        base = RunnerEnrichment(self.date_from).build(history, side).drop(columns=list(_FORECAST_COLUMNS), errors="ignore")
        base = base.merge(PriorRaceBias().of(PriorRaceBias.load(self.slopes)), on="race_id", how="left")
        return [self._write(base, timing) for timing in _FORECAST_FOLDER]

    def load(self, timing: PredictionTiming) -> pd.DataFrame:
        return pd.read_pickle(self.path(timing))

    def path(self, timing: PredictionTiming) -> Path:
        return self.root / f"材料-{timing.value}.pkl"

    @staticmethod
    def _empty(keys: list[str], values: tuple[str, ...]) -> pd.DataFrame:
        """展開の予想を結ばないときの空の表（材料は時点ごとに後から結ぶ）。"""
        return pd.DataFrame({**{key: pd.Series(dtype=str) for key in keys}, **{value: pd.Series(dtype=float) for value in values}})

    def _write(self, base: pd.DataFrame, timing: PredictionTiming) -> Path:
        store = PaceForecastStore(_FORECAST_ROOT / _FORECAST_FOLDER[timing])
        frame = base.merge(store.races(), on="race_id", how="left").merge(store.horses(), on=["race_id", "horse_id"], how="left")
        table = ScenarioMaterials(race_day=timing == PredictionTiming.RACE_DAY).build(frame)
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.path(timing)
        table.to_pickle(path)
        return path
