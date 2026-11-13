"""WIN5 の対象レース（開催日・何レース目・レースID）を読む（1 SQL）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import duckdb
import pandas as pd

from 共通 import facts, keys

_DAY_TABLE = "wf"
_RACE_TABLE = "wf__重勝式対象レース情報"
_DAY_COLUMNS = ("開催年", "開催月日", "データ区分")
_RACE_COLUMNS = ("開催年", "開催月日", "_連番", *keys.RACE_KEY[2:])
#: 中止の回のデータ区分。対象レースが走られていないので読まない。
_CANCELLED = "9"


@dataclass(frozen=True)
class Win5LegRepository:
    """``date_from`` 以降の WIN5 の対象レース。1行 = 1つの対象レース。列は race_date・leg（1〜5）・race_id。

    成績の版（月曜）だけでなく、速報の版（当日）の回も読む（その日の WIN5 も事例に入れるため）。中止の回は読まない。
    """

    con: duckdb.DuckDBPyConnection

    def load(self, date_from: date) -> pd.DataFrame:
        day_table = facts.optional_relation(self.con, _DAY_TABLE, _DAY_COLUMNS)
        race_table = facts.optional_relation(self.con, _RACE_TABLE, _RACE_COLUMNS)
        year, mmdd = keys.q("開催年"), keys.q("開催月日")
        race_id = " || ".join(keys.col(name, "t") for name in keys.RACE_KEY)
        sql = f"""
        SELECT DISTINCT {keys.race_date_expr('t')} AS race_date, TRY_CAST(t.{keys.q('_連番')} AS INTEGER) AS leg, {race_id} AS race_id
        FROM {race_table} AS t
        JOIN {day_table} AS w USING ({year}, {mmdd})
        WHERE w.{keys.q('データ区分')} <> '{_CANCELLED}' AND t.{year} || t.{mmdd} >= ?
        ORDER BY race_date, leg
        """
        return self.con.execute(sql, [date_from.strftime("%Y%m%d")]).df()
