"""元DB の事実表から型の材料の表を作り、reports/ に保存する（学習のたびに元DB を読まないため）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from ..enrichment.runner_enrichment import RunnerEnrichment
from ..repository import RunnerFactsRepository, Win5LegRepository
from ..theory.runner_type_flags import RunnerTypeFlags
from .type_features import TypeFeatures

#: 保存するファイルの名前。
FILE_NAME = "型の材料.pkl"
#: 予測の無い出走の表を作るための、空の予測。
_NO_PREDICTIONS = pd.DataFrame({"race_id": pd.Series(dtype=str), "horse_no": pd.Series(dtype=float), "model": pd.Series(dtype=float)})


@dataclass(frozen=True)
class TypeFeatureSource:
    """``date_from`` 以降の平地の出走の型の材料。過去走は ``history_from`` からたどる（2012年の行でも過去走がそろうように）。"""

    folder: Path
    date_from: date = date(2012, 1, 1)
    history_from: date = date(2006, 1, 1)

    @property
    def path(self) -> Path:
        return self.folder / FILE_NAME

    def build(self, con: duckdb.DuckDBPyConnection) -> Path:
        history = RunnerFactsRepository(con).load(self.history_from)
        legs = Win5LegRepository(con).load(self.date_from)
        runners = RunnerEnrichment((_NO_PREDICTIONS,), self.date_from).build(history, legs)
        features = TypeFeatures().build(RunnerTypeFlags().add(runners))
        self.folder.mkdir(parents=True, exist_ok=True)
        features.to_pickle(self.path)
        return self.path

    def load(self) -> pd.DataFrame:
        if not self.path.exists():
            raise FileNotFoundError(f"型の材料がありません: {self.path}（forecast.py features で作る）")
        return pd.read_pickle(self.path)
