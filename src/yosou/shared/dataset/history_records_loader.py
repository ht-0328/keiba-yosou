"""学習用に、ある日以降の全部の出走の記録を集める。"""

from __future__ import annotations

from datetime import date

import duckdb

from ..feature import EntryRecords
from ..repository import (
    FactTableRepository,
    MarketRunRepository,
    RaceEarlyRecordRepository,
    StakesTendencyRepository,
    TargetScope,
)
from .ability_sources_loader import AbilitySourcesLoader
from .entry_records_loader import EntryRecordsLoader
from .pool_probability_loader import PoolProbabilityLoader


class HistoryRecordsLoader:
    """開催日が ``first_day`` 以降の、中央の確定成績の出走の記録を集める（学習データ用）。

    ``race_history``・``stakes_tendency``・``market_runs``・``ability_sources``・``pool_probabilities`` は
    ``EntryRecordsLoader`` にそのまま渡す
    （レースごとの序盤と後半の記録・重賞のレースごとの傾向・過去の全出走のオッズと着順・馬の力の材料の元の記録・
    券種ごとのオッズから見た確率。省略すると読まない）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection,
                 race_history: RaceEarlyRecordRepository | None = None,
                 stakes_tendency: StakesTendencyRepository | None = None,
                 market_runs: MarketRunRepository | None = None,
                 ability_sources: AbilitySourcesLoader | None = None,
                 pool_probabilities: PoolProbabilityLoader | None = None) -> None:
        self._fact_table = FactTableRepository(con)
        self._records_loader = EntryRecordsLoader(
            con, race_history, stakes_tendency, market_runs, ability_sources, pool_probabilities,
        )

    def load(self, first_day: date) -> EntryRecords:
        self._fact_table.ensure()
        return self._records_loader.load(TargetScope.since(first_day))
