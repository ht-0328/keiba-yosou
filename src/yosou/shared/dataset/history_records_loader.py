"""学習用に、ある日以降の全部の出走の記録を集める。"""

from __future__ import annotations

from datetime import date

import duckdb

from ..feature import EntryRecords
from ..repository import FactTableRepository, RaceEarlyRecordRepository, TargetScope
from .entry_records_loader import EntryRecordsLoader


class HistoryRecordsLoader:
    """開催日が ``first_day`` 以降の、中央の確定成績の出走の記録を集める（学習データ用）。

    ``race_history`` は ``EntryRecordsLoader`` にそのまま渡す（レースごとの序盤と後半の記録。省略すると読まない）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection,
                 race_history: RaceEarlyRecordRepository | None = None) -> None:
        self._fact_table = FactTableRepository(con)
        self._records_loader = EntryRecordsLoader(con, race_history)

    def load(self, first_day: date) -> EntryRecords:
        self._fact_table.ensure()
        return self._records_loader.load(TargetScope.since(first_day))
