"""対象の出走の記録を集める。"""

from __future__ import annotations

import duckdb
import pandas as pd

from ..feature import PEOPLE_WINDOW_DAYS, WORKOUT_WINDOW_DAYS, EntryRecords, WorkoutCoverage
from ..repository import (
    CareerCountRepository,
    EntryRepository,
    PastRunRepository,
    PedigreeDayRepository,
    PeopleDayRepository,
    TargetScope,
    WorkoutCoverageRepository,
    WorkoutRepository,
)

#: 出走の行と、出走別着度数の行を突き合わせる鍵。
_ENTRY_KEY = ["race_id", "horse_id"]


class EntryRecordsLoader:
    """リポジトリを順に呼んで、対象の出走の記録（``EntryRecords``）を集める。SQL は持たない。"""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._entries = EntryRepository(con)
        self._career_counts = CareerCountRepository(con)
        self._past_runs = PastRunRepository(con)
        self._workouts = WorkoutRepository(con, WORKOUT_WINDOW_DAYS)
        self._workout_coverage = WorkoutCoverageRepository(con)
        self._jockey_days = PeopleDayRepository.for_jockeys(con, PEOPLE_WINDOW_DAYS)
        self._trainer_days = PeopleDayRepository.for_trainers(con, PEOPLE_WINDOW_DAYS)
        self._sire_days = PedigreeDayRepository.for_sires(con, PEOPLE_WINDOW_DAYS)
        self._damsire_days = PedigreeDayRepository.for_damsires(con, PEOPLE_WINDOW_DAYS)

    def load(self, scope: TargetScope) -> EntryRecords:
        """``scope`` の出走の記録。"""
        entries = self._entries.read(scope)
        career_counts = self._career_counts.read(scope)
        return EntryRecords(
            entries=self._with_career_counts(entries, career_counts),
            past_runs=self._past_runs.read(scope),
            workouts=self._workouts.read(scope),
            workout_coverage=WorkoutCoverage.from_table(self._workout_coverage.read()),
            jockey_days=self._jockey_days.read(scope),
            trainer_days=self._trainer_days.read(scope),
            sire_days=self._sire_days.read(scope),
            damsire_days=self._damsire_days.read(scope),
        )

    def _with_career_counts(self, entries: pd.DataFrame, career_counts: pd.DataFrame) -> pd.DataFrame:
        """出走の行に、その出走の出走別着度数（``ck_`` で始まる列）を付ける。無い出走は欠損値。"""
        return entries.merge(career_counts, on=_ENTRY_KEY, how="left")
