"""調教（坂路・ウッド）を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts, keys

from .target_scope import TargetScope

#: 調教の表と、そのコースの名前。hc = 坂路調教、wc = ウッドチップ調教。``WorkoutCoverageRepository`` と共有する。
COURSE_BY_TABLE: dict[str, str] = {"hc": "坂路", "wc": "ウッド"}
_FOUR_FURLONGS = "4ハロンタイム合計(800M～0M)"
_LAST_FURLONG = "ラップタイム(200M～0M)"
_NEEDED_COLUMNS = ("データ区分", "調教年月日", "調教時刻", keys.HORSE_KEY, _FOUR_FURLONGS, _LAST_FURLONG)
#: 削除されたレコードのデータ区分。
DELETED = "0"


class WorkoutRepository:
    """対象の出走それぞれの、開催日の前 ``window_days`` 日以内の調教を読む。坂路とウッドを1つの表にする。"""

    def __init__(self, con: duckdb.DuckDBPyConnection, window_days: int) -> None:
        self._con = con
        self._window_days = window_days

    def read(self, scope: TargetScope) -> pd.DataFrame:
        """1行 = 調教1本。馬・調教の日時の古い順に並べる。タイムは秒（測定不良は欠損値）。"""
        tables = [self._table_sql(table, course) for table, course in COURSE_BY_TABLE.items()]
        sql = f"""
        WITH wanted AS (
            SELECT DISTINCT horse_id, CAST(race_date AS DATE) AS race_day FROM {scope.relation}
        ), sessions AS (
            {" UNION ALL ".join(tables)}
        )
        SELECT s.* FROM sessions s
        WHERE EXISTS (
            SELECT 1 FROM wanted w
            WHERE w.horse_id = s.horse_id
              AND s.work_date BETWEEN w.race_day - {self._window_days} AND w.race_day - 1
        )
        ORDER BY s.horse_id, s.work_date, s.work_time
        """
        return self._con.execute(sql).df()

    def _table_sql(self, table: str, course: str) -> str:
        """調教の表1つを、馬・日・時刻・コース・4ハロン・ラスト1ハロンの形にする。表が無ければ空の関係。"""
        relation = facts.optional_relation(self._con, table, _NEEDED_COLUMNS)
        four_furlongs = self._seconds_sql(_FOUR_FURLONGS, no_time="0000", over_limit="9999")
        last_furlong = self._seconds_sql(_LAST_FURLONG, no_time="000", over_limit="999")
        return f"""
            SELECT {keys.q(keys.HORSE_KEY)} AS horse_id,
                   CAST(TRY_STRPTIME({keys.q('調教年月日')}, '%Y%m%d') AS DATE) AS work_date,
                   {keys.q('調教時刻')} AS work_time, '{course}' AS course,
                   {four_furlongs} AS four_furlongs, {last_furlong} AS last_furlong
            FROM {relation}
            WHERE {keys.q('データ区分')} <> '{DELETED}'
        """

    def _seconds_sql(self, column: str, *, no_time: str, over_limit: str) -> str:
        """0.1秒単位の文字列を秒にする式。測定不良（``no_time``）と上限超え（``over_limit``）は NULL。"""
        valid = f"NULLIF(NULLIF({keys.q(column)}, '{no_time}'), '{over_limit}')"
        return f"TRY_CAST({valid} AS INTEGER) / 10.0"
