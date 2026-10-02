"""レースごとの、序盤と後半の記録を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts

from .target_scope import TargetScope

#: 1レースに1つの値の列（意味は ``tools/共通/facts.py`` の ``FACT_COLUMNS``）。
_RACE_COLUMNS: tuple[str, ...] = (
    "venue_code", "track_code", "surface", "distance_m", "class_order", "field_size",
    "first_corner_no", "corner_count", "corner_laps_over_one", "first_corner_leader_no", "first3f", "last3f_race",
)


class RaceEarlyRecordRepository:
    """対象の最初の開催日の ``window_days`` 日前から、最後の開催日までの平地のレースを、1行 = 1レースで読む（設計書 04 の 2）。

    コースの形（M）と、前半・後半タイムの基準の元になる。確定成績の事実表に、対象の関係（予測するレース。成績はまだ無い）を
    足して読むので、予測するレースにも条件の列が入る。成績の確定したレースかは ``finished``（着順のある馬がいるか）で分かる。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, window_days: int) -> None:
        self._con = con
        self._window_days = window_days

    def read(self, scope: TargetScope) -> pd.DataFrame:
        """列は ``race_id``・``race_date``（日付型）・``_RACE_COLUMNS``・``finished``。開催日・レースID の順。"""
        columns = ", ".join(("race_id", "race_date", "ran", "finish", *_RACE_COLUMNS))
        picked = ", ".join(f"any_value({column}) AS {column}" for column in _RACE_COLUMNS)
        first_day = f"(SELECT min(CAST(race_date AS DATE)) FROM {scope.relation}) - {self._window_days}"
        last_day = f"(SELECT max(CAST(race_date AS DATE)) FROM {scope.relation})"
        sql = f"""
        WITH rows AS (
            SELECT {columns} FROM {facts.FACTS_TABLE}
            WHERE CAST(race_date AS DATE) >= {first_day} AND CAST(race_date AS DATE) <= {last_day}
            UNION ALL
            SELECT {columns} FROM {scope.relation}
        )
        SELECT race_id, min(CAST(race_date AS DATE)) AS race_date, {picked},
               bool_or(ran AND finish IS NOT NULL) AS finished
        FROM rows
        WHERE surface IN ('芝', 'ダート')
        GROUP BY race_id
        ORDER BY race_date, race_id
        """
        return self._con.execute(sql).df()
