"""速報の馬体重を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts, keys

#: 速報の馬体重は、親の表 wh の子の表（馬番ごとの行）に入っている。
_TABLE = "wh__馬体重情報"
_NEEDED_COLUMNS = (*keys.RACE_KEY, "馬番", "馬体重", "増減符号", "増減差")
#: 馬体重の「出走取消」（000）と「計量不能」（999）。馬体重として使わない。
_NO_WEIGHT_VALUES: tuple[str, ...] = ("000", "999")
#: 増減差の「計量不能」。
_NO_CHANGE_VALUE = "999"


class AnnouncedWeightRepository:
    """速報の馬体重（当日、発走の前に発表される）から、1レースの馬番ごとの馬体重と増減を読む。"""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, race_id: str) -> pd.DataFrame:
        """列は ``horse_no``・``body_weight``・``weight_change``（kg）。速報が無ければ空の表。"""
        table = facts.optional_relation(self._con, _TABLE, _NEEDED_COLUMNS)
        sign = keys.q("増減符号")
        change = f"TRY_CAST(NULLIF({keys.q('増減差')}, '{_NO_CHANGE_VALUE}') AS INTEGER)"
        sql = f"""
        SELECT TRY_CAST({keys.q('馬番')} AS INTEGER) AS horse_no,
               TRY_CAST({keys.q('馬体重')} AS INTEGER) AS body_weight,
               CASE WHEN {sign} = '+' THEN {change}
                    WHEN {sign} = '-' THEN -{change}
                    WHEN {change} = 0 THEN 0 END AS weight_change
        FROM {table}
        WHERE {keys.rid_expr()} = ?
          AND {keys.q('馬体重')} NOT IN {keys.sql_list(_NO_WEIGHT_VALUES)}
          AND TRY_CAST({keys.q('馬体重')} AS INTEGER) IS NOT NULL
        ORDER BY horse_no
        """
        return self._con.execute(sql, [race_id]).df()
