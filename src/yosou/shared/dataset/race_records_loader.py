"""予測用に、1レースの出走馬の記録を集める。"""

from __future__ import annotations

from collections.abc import Mapping

import duckdb

from ..feature import EntryRecords
from ..repository import (
    AnnouncedGoingRepository,
    AnnouncedWeightRepository,
    FactTableRepository,
    RaceEarlyRecordRepository,
    RaceEntryTableRepository,
    ScratchRepository,
)
from .announced_odds_applier import AnnouncedOddsApplier
from .announced_weight_applier import AnnouncedWeightApplier
from .entry_records_loader import EntryRecordsLoader
from .scratch_applier import ScratchApplier


class RaceRecordsLoader:
    """1レースの出走馬の記録を集める（予測用データ用）。確定前のレースでも、終わったレースでもよい。

    その時点で DB に速報（馬場状態・馬体重・出走取消）があれば、出走の行に反映する。
    予測に使う人気・オッズが渡されれば、それも出走の行に反映する。
    ``race_history`` は ``EntryRecordsLoader`` にそのまま渡す（レースごとの序盤と後半の記録。省略すると読まない）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection,
                 race_history: RaceEarlyRecordRepository | None = None) -> None:
        self._fact_table = FactTableRepository(con)
        self._race_entry_table = RaceEntryTableRepository(con)
        self._announced_going = AnnouncedGoingRepository(con)
        self._announced_weights = AnnouncedWeightRepository(con)
        self._scratches = ScratchRepository(con)
        self._records_loader = EntryRecordsLoader(con, race_history)
        self._weight_applier = AnnouncedWeightApplier()
        self._scratch_applier = ScratchApplier()
        self._odds_applier = AnnouncedOddsApplier()

    def load(self, race_id: str, popularity: Mapping[int | str, int] | None = None,
             odds: Mapping[int, float] | None = None) -> EntryRecords:
        """レースが無ければ ``LookupError``、rid の形が違えば ``ValueError``。

        ``popularity`` は 馬番（木曜は馬名）→ 単勝人気、``odds`` は 馬番 → 単勝オッズ（倍）。
        渡すと、出走の行の値をそれにする（まだ DB に無いときに、手で渡すか締め切り前の値から作る）。
        """
        self._fact_table.ensure()
        going_code = self._announced_going.read(race_id)
        scope = self._race_entry_table.build(race_id, going_code, popularity)
        records = self._records_loader.load(scope)
        weighed = self._weight_applier.apply(records.entries, self._announced_weights.read(race_id))
        declared = self._scratch_applier.apply(weighed, self._scratches.read(race_id))
        priced = self._odds_applier.apply(declared, odds)
        return records.with_entries(priced)
