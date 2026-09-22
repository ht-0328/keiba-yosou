"""調教の記録が DB にある期間（コースごとの最初の日）を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts, keys

from .workout_repository import COURSE_BY_TABLE, DELETED

_NEEDED_COLUMNS = ("データ区分", "調教年月日")


class WorkoutCoverageRepository:
    """調教のコース（坂路・ウッド）ごとに、DB にある記録の最初の調教日を読む。

    JRA-VAN のウッドチップ調教は 2021年7月27日から提供が始まったので、それより前の出走には
    ウッドの記録そのものが無い。特徴量を作る側は、この日を見て「記録が無い」と「調教していない」を
    区別する（設計書 09 の I）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self) -> pd.DataFrame:
        """1行 = 1コース。列は ``course``・``first_day``。記録が1本も無いコース（表が無い DB など）の行は無い。"""
        tables = [self._table_sql(table, course) for table, course in COURSE_BY_TABLE.items()]
        sql = f"""
        SELECT course, CAST(TRY_STRPTIME(min({keys.q('調教年月日')}), '%Y%m%d') AS DATE) AS first_day
        FROM ({" UNION ALL ".join(tables)})
        GROUP BY course
        ORDER BY course
        """
        return self._con.execute(sql).df()

    def _table_sql(self, table: str, course: str) -> str:
        """調教の表1つを、コース・調教年月日の形にする。表が無ければ空の関係。"""
        relation = facts.optional_relation(self._con, table, _NEEDED_COLUMNS)
        return f"""
            SELECT '{course}' AS course, {keys.q('調教年月日')}
            FROM {relation}
            WHERE {keys.q('データ区分')} <> '{DELETED}'
        """
