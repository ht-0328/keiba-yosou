"""騎手か調教師の、日ごとの成績を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts

from .target_scope import TargetScope


class PeopleDayRepository:
    """対象の出走に関わる騎手（か調教師）ごと、開催日ごとの、出走数と3着以内の数を読む。

    期間は、対象のいちばん早い開催日の ``window_days`` 日前から、いちばん遅い開催日の前日まで。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, code_column: str, window_days: int) -> None:
        self._con = con
        self._code_column = code_column
        self._window_days = window_days

    @classmethod
    def for_jockeys(cls, con: duckdb.DuckDBPyConnection, window_days: int) -> PeopleDayRepository:
        """騎手の成績を読むリポジトリ。"""
        return cls(con, "jockey_code", window_days)

    @classmethod
    def for_trainers(cls, con: duckdb.DuckDBPyConnection, window_days: int) -> PeopleDayRepository:
        """調教師の成績を読むリポジトリ。"""
        return cls(con, "trainer_code", window_days)

    def read(self, scope: TargetScope) -> pd.DataFrame:
        """1行 = 1人の1日。人・開催日の古い順に並べる。"""
        code = self._code_column
        first_race_day = f"(SELECT min(CAST(race_date AS DATE)) FROM {scope.relation})"
        sql = f"""
        SELECT {code} AS person_code, CAST(race_date AS DATE) AS race_date,
               CAST(count(*) AS INTEGER) AS starts,
               CAST(sum(CASE WHEN finish <= 3 THEN 1 ELSE 0 END) AS INTEGER) AS places
        FROM {facts.FACTS_TABLE}
        WHERE ran
          AND {code} IN (SELECT {code} FROM {scope.relation})
          AND race_date < (SELECT max(race_date) FROM {scope.relation})
          AND CAST(race_date AS DATE) >= {first_race_day} - {self._window_days}
        GROUP BY ALL
        ORDER BY person_code, race_date
        """
        return self._con.execute(sql).df()
