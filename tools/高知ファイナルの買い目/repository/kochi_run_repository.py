"""事実表から、高知の出走（1行 = 1頭）を読む。これから走る1レースの出走馬の表を足せる（SQL は1つ）。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import keys
from 共通.facts import FACTS_TABLE

from ..final_columns import RAW_COLUMNS

VENUE = "高知"
_COLUMNS = ", ".join(RAW_COLUMNS)
#: ``{entries}`` はこれから走るレースの出走馬の関係（無ければ空の関係）。事実表にもう入っているレースの行は足さない。
_SQL = """
SELECT {columns} FROM {facts} WHERE venue = '{venue}'
UNION ALL
SELECT {columns} FROM {entries} e WHERE e.venue = '{venue}' AND e.race_id NOT IN (SELECT race_id FROM {facts} WHERE venue = '{venue}')
ORDER BY race_id, horse_no
"""


class KochiRunRepository:
    """列は ``RAW_COLUMNS``（事実表と同じ名前）。``entry_table`` は ``facts.build_entry_facts`` が作る一時表の名前。
    事実表（一時表 ``facts``）は呼ぶ側が先に作っておく。"""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, entry_table: str | None = None) -> pd.DataFrame:
        facts = keys.q(FACTS_TABLE)
        entries = keys.q(entry_table) if entry_table else f"(SELECT * FROM {facts} WHERE FALSE)"
        return self._con.execute(_SQL.format(columns=_COLUMNS, facts=facts, entries=entries, venue=VENUE)).df()
