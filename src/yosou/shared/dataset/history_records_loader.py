"""学習用に、ある日以降の全部の出走の記録を集める。"""

from __future__ import annotations

from datetime import date

import duckdb

from 共通 import facts

from ..feature import EntryRecords
from ..repository import (
    CareerCountRepository,
    FactTableRepository,
    HeadToHeadRunRepository,
    MarketRunRepository,
    RaceEarlyRecordRepository,
    StakesTendencyRepository,
    TargetScope,
)
from .ability_sources_loader import AbilitySourcesLoader
from .finish_records_loader import FinishRecordsLoader
from .entry_records_loader import EntryRecordsLoader
from .pool_probability_loader import PoolProbabilityLoader


class HistoryRecordsLoader:
    """開催日が ``first_day`` 以降の、中央の確定成績の出走の記録を集める（学習データ用）。

    ``race_history``・``stakes_tendency``・``market_runs``・``ability_sources``・``pool_probabilities``・``head_to_head_runs`` は
    ``EntryRecordsLoader`` にそのまま渡す
    （レースごとの序盤と後半の記録・重賞のレースごとの傾向・過去の全出走のオッズと着順・馬の力の材料の元の記録・
    券種ごとのオッズから見た確率・対戦レーティングの元になる過去の全出走の着順。``finish_records`` は勝ち切る材料の元の記録。省略すると読まない）。
    ``facts_source`` は事実表の元データの決めごと（中央か地方か。省略すると元DB の表から見分ける）、``career_counts`` は
    出走別着度数を読むリポジトリ（省略すると中央の ``ck``）。地方の予想が渡す（地方の設計書 04 の 3）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection,
                 race_history: RaceEarlyRecordRepository | None = None,
                 stakes_tendency: StakesTendencyRepository | None = None,
                 market_runs: MarketRunRepository | None = None,
                 ability_sources: AbilitySourcesLoader | None = None,
                 pool_probabilities: PoolProbabilityLoader | None = None,
                 head_to_head_runs: HeadToHeadRunRepository | None = None,
                 finish_records: FinishRecordsLoader | None = None,
                 facts_source: facts.FactsSource | None = None,
                 career_counts: CareerCountRepository | None = None) -> None:
        self._fact_table = FactTableRepository(con, facts_source)
        self._records_loader = EntryRecordsLoader(
            con, race_history, stakes_tendency, market_runs, ability_sources, pool_probabilities, head_to_head_runs, finish_records,
            career_counts=career_counts,
        )

    def load(self, first_day: date) -> EntryRecords:
        self._fact_table.ensure()
        return self._records_loader.load(TargetScope.since(first_day))
