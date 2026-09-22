"""予測する1レースの出走馬の一時表を作る。"""

from __future__ import annotations

import duckdb

from 共通 import facts

from .target_scope import TargetScope

#: 作る一時表の名前。
_TABLE = "form_aptitude_race_entries"


class RaceEntryTableRepository:
    """1レースの出走馬に、事実表と同じ列（前走・累積など）を付けた一時表を作る。

    事実表と同じ SQL を「確定成績 + そのレース」に当てるので、学習と予測で列の定義がずれない（設計書 11 の 4）。
    確定前のレース（出走馬名表・出馬表）でも、終わったレースでもよい。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def build(self, race_id: str, going_code: str | None) -> TargetScope:
        """一時表を作り、その出走を指す ``TargetScope`` を返す。レースが無ければ ``LookupError``。

        ``going_code`` は速報の馬場状態コード。None なら、レースの行に入っている馬場状態を使う。
        """
        scope = facts.EntryScope(race_id, going_code)
        table = facts.build_entry_facts(self._con, scope, name=_TABLE)
        return TargetScope.of_table(table)
