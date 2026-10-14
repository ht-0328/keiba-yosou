"""予測する1レースの登録馬の一時表を作る。"""

from __future__ import annotations

import duckdb

from 共通 import facts, registration

from yosou.shared.repository import TargetScope
from yosou.shared.repository.target_scope import AS_OF_COLUMN

#: 作る一時表の名前（事実表と同じ列の表と、締めの日の列を足した表）。
_FACTS_TABLE = "yosou_registration_facts"
TABLE = "yosou_registration_entries"
#: 特別登録が無いときの案内（jvdata-store の取り込み方。README の「取得する範囲」を参照）。
_GUIDANCE = (
    "特別登録が元DB にありません: {race_id}。jvdata-store で特別登録を取り込んでください"
    "（今週・来週分は `uv run jvstore sync`、過去分は `uv run jvstore fetch --dataspec TOKU --option 1 --from <開始時刻 YYYYMMDDhhmmss>`）。"
)


class RegistrationEntryTableRepository:
    """1レースの登録馬に、事実表と同じ列（前走・累積など）と材料の締めの日（登録日相当）を付けた一時表を作る（設計書 04・06 の図2）。

    特別登録（``tk``・``tk__登録馬毎情報``）から作った登録馬の行（``registration.registration_rows_sql``）を、そのレースの ``ra``・``se``
    の代わりに事実表と同じ SQL（``facts.build_entry_facts``）に渡すので、学習と予測で列の定義がずれない。月曜の版（ハンデ発表後）が
    無ければ日曜の版を使う。木曜以降に出走馬名表が元DB にあっても読まない（設計書 11 の 7）。
    ``as_of_sql`` は、開催日の列から締めの日を作る SQL の式（``RegistrationCutoff.sql``）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, as_of_sql: str) -> None:
        self._con = con
        self._as_of_sql = as_of_sql

    def build(self, race_id: str) -> TargetScope:
        """一時表を作り、その登録馬を指す ``TargetScope`` を返す。特別登録が無ければ、取り込み方を添えて ``LookupError``。"""
        rows = registration.registration_rows_sql(self._con, race_id)
        try:
            facts.build_entry_facts(self._con, facts.EntryScope(race_id), name=_FACTS_TABLE, rows=rows)
        except LookupError as error:
            raise LookupError(_GUIDANCE.format(race_id=race_id)) from error
        self._con.execute(
            f"CREATE OR REPLACE TEMP TABLE {TABLE} AS "
            f"SELECT *, {self._as_of_sql} AS {AS_OF_COLUMN} FROM {_FACTS_TABLE}"
        )
        return TargetScope.of_table(TABLE, AS_OF_COLUMN)
