"""予測用に、1レースの登録馬の記録を集める。"""

from __future__ import annotations

from collections.abc import Mapping

import duckdb

from yosou.shared.dataset import AbilitySourcesLoader
from yosou.shared.dataset.entry_records_loader import EntryRecordsLoader
from yosou.shared.feature import EntryRecords
from yosou.shared.repository import FactTableRepository, HeadToHeadRunRepository

from ..repository import RegistrationEntryTableRepository


class RegistrationRecordsLoader:
    """1レースの登録馬の記録を集める（予測用データ用。設計書 05 の図4）。

    事実表を用意し（``FactTableRepository``）、特別登録から登録馬の行の一時表を作り（``RegistrationEntryTableRepository``）、
    共通の ``EntryRecordsLoader`` で記録を集める。速報（馬場状態・馬体重・取消）とオッズは読まない（この時点には無く、あっても使わない）。
    ``RaceRecordsLoader`` と同じ ``load(レースID, 単勝人気=省略可, 単勝オッズ=省略可)`` の形を守り、人気とオッズは受け取っても使わない
    （``DatasetBuilder`` がそのまま使えるようにするため）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, entry_table: RegistrationEntryTableRepository,
                 ability_sources: AbilitySourcesLoader, head_to_head_runs: HeadToHeadRunRepository) -> None:
        self._fact_table = FactTableRepository(con)
        self._entry_table = entry_table
        self._records_loader = EntryRecordsLoader(con, ability_sources=ability_sources, head_to_head_runs=head_to_head_runs)

    def load(self, race_id: str, popularity: Mapping[int | str, int] | None = None,
             odds: Mapping[int, float] | None = None) -> EntryRecords:
        """特別登録が無ければ ``LookupError``、rid の形が違えば ``ValueError``。``popularity``・``odds`` は使わない。"""
        self._fact_table.ensure()
        scope = self._entry_table.build(race_id)
        return self._records_loader.load(scope)
