"""保存した予測と学習データの表と元DB から、3回目の材料表を組み立てる。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from yosou.shared.dataset import RACE_DATE
from yosou.shared.dataset.column_names import PLACE_ODDS_HIGH, PLACE_ODDS_LOW, PLACE_PAYOUT
from yosou.shared.repository import RaceDayRange

from ..repository import RaceFactRepository
from . import columns as c
from .material_sources import MaterialSources, PredictionSource
from .materials import Round3Materials
from .race_table_builder import RaceTableBuilder
from .runner_table_builder import RunnerTableBuilder
from .truth_table_reader import TruthTableReader

#: 払戻の履歴の列（学習データの表の列 → 材料表の列）。
_HISTORY_RENAME = {RACE_DATE: c.RACE_DATE, PLACE_ODDS_LOW: c.PLACE_ODDS, PLACE_ODDS_HIGH: c.PLACE_ODDS_HIGH, PLACE_PAYOUT: c.PLACE_PAYOUT}


class MaterialsBuilder:
    """4つの予測（``MaterialSources``）と学習データの表を読み、元DB からレースの属性（重賞か）を読んで ``Round3Materials`` を作る。

    元DB を開くのはレースの属性を読む間だけ（``RaceFactRepository``。事実表が無ければ作るので、接続ごとに1回、約20秒）。
    """

    def __init__(self, sources: MaterialSources, con: duckdb.DuckDBPyConnection) -> None:
        self._sources = sources
        self._con = con

    def build(self) -> Round3Materials:
        form = self._read(self._sources.form)
        truth = TruthTableReader(self._sources.form_tables).read()
        runners = RunnerTableBuilder().build(form, truth, self._read(self._sources.longshots), self._read(self._sources.favorites))
        facts = RaceFactRepository(self._con).read(self._days_of(runners))
        races = RaceTableBuilder().build(runners, self._read(self._sources.upset), facts)
        history = truth[list(_HISTORY_RENAME)].rename(columns=_HISTORY_RENAME)
        history[c.RACE_DATE] = pd.to_datetime(history[c.RACE_DATE])
        return Round3Materials(runners, races, history)

    def _read(self, source: PredictionSource) -> pd.DataFrame:
        if not source.path.exists():
            raise FileNotFoundError(f"予測の表がありません: {source.path}")
        return pd.read_pickle(source.path)

    def _days_of(self, runners: pd.DataFrame) -> RaceDayRange:
        days = pd.to_datetime(runners[c.RACE_DATE])
        return RaceDayRange(date.fromisoformat(str(days.min().date())), date.fromisoformat(str(days.max().date())))
