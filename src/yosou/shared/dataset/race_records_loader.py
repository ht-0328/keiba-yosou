"""予測用に、1レースの出走馬の記録を集める。"""

from __future__ import annotations

from collections.abc import Mapping

import duckdb

from ..feature import EntryRecords
from ..repository import (
    AnnouncedGoingRepository,
    AnnouncedWeightRepository,
    FactTableRepository,
    RaceEntryTableRepository,
    ScratchRepository,
)
from .announced_weight_applier import AnnouncedWeightApplier
from .entry_records_loader import EntryRecordsLoader
from .scratch_applier import ScratchApplier


class RaceRecordsLoader:
    """1レースの出走馬の記録を集める（予測用データ用）。確定前のレースでも、終わったレースでもよい。

    その時点で DB に速報（馬場状態・馬体重・出走取消）があれば、出走の行に反映する。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._fact_table = FactTableRepository(con)
        self._race_entry_table = RaceEntryTableRepository(con)
        self._announced_going = AnnouncedGoingRepository(con)
        self._announced_weights = AnnouncedWeightRepository(con)
        self._scratches = ScratchRepository(con)
        self._records_loader = EntryRecordsLoader(con)
        self._weight_applier = AnnouncedWeightApplier()
        self._scratch_applier = ScratchApplier()

    def load(self, race_id: str, popularity: Mapping[int, int] | None = None) -> EntryRecords:
        """レースが無ければ ``LookupError``、rid の形が違えば ``ValueError``。

        ``popularity`` は 馬番 → 単勝人気。渡すと、出走の行の単勝人気をその値にする（まだ DB に無いときに手で渡す）。
        """
        self._fact_table.ensure()
        going_code = self._announced_going.read(race_id)
        scope = self._race_entry_table.build(race_id, going_code, popularity)
        records = self._records_loader.load(scope)
        weighed = self._weight_applier.apply(records.entries, self._announced_weights.read(race_id))
        declared = self._scratch_applier.apply(weighed, self._scratches.read(race_id))
        return records.with_entries(declared)
