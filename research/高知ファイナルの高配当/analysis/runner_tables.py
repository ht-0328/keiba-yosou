"""出走の表を作る流れ: 元DB の高知の出走 → 材料を付ける → ファイナルレースの出走馬を取り出す。"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import pandas as pd

from .final_runners import FinalRunners
from .kochi_run_features import KochiRunFeatures
from .popularity_band import PopularityBand
from .repository import KochiRunsRepository


@dataclass(frozen=True)
class RunnerTables:
    """``load`` が（材料つきの高知の全出走, ファイナルレースの出走馬）を返す。前者は近走を1走ずつ見るときに使う。"""

    con: duckdb.DuckDBPyConnection
    min_heads: int = 9
    popularity: PopularityBand = PopularityBand()

    def load(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        runs = KochiRunFeatures().build(KochiRunsRepository(self.con).load())
        return runs, FinalRunners(self.min_heads, self.popularity).select(runs)
