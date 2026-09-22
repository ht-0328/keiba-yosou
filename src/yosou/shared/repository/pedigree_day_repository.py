"""血統（父・母父）の産駒の、日ごとの成績を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts

from .target_scope import TargetScope

#: 事実表の、血統の名前の列（父・父の父・母父）。
SIRE, GRANDSIRE, DAMSIRE = "sire", "grandsire", "damsire"


class PedigreeDayRepository:
    """対象の出走に関わる血統ごと、開催日ごと、芝ダごとの、産駒の出走数と3着以内の数を読む。

    **「産駒の成績」は、その血統を持つ馬たちが走った成績。** 種牡馬自身が現役だったころの成績ではない。
    芝ダごとに分けて読むので、読む側で「芝ダを問わない力」と「その芝ダでの適性」の両方を数えられる。
    期間は、対象のいちばん早い開催日の ``window_days`` 日前から、いちばん遅い開催日の前日まで。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, name_column: str, window_days: int) -> None:
        """``name_column`` は事実表の ``sire``・``grandsire``・``damsire`` のどれか。"""
        self._con = con
        self._name_column = name_column
        self._window_days = window_days

    @classmethod
    def for_sires(cls, con: duckdb.DuckDBPyConnection, window_days: int) -> PedigreeDayRepository:
        """父の産駒の成績を読むリポジトリ。"""
        return cls(con, SIRE, window_days)

    @classmethod
    def for_damsires(cls, con: duckdb.DuckDBPyConnection, window_days: int) -> PedigreeDayRepository:
        """母父の産駒の成績を読むリポジトリ。"""
        return cls(con, DAMSIRE, window_days)

    def read(self, scope: TargetScope) -> pd.DataFrame:
        """1行 = 1つの血統の、1日の、1つの芝ダ。列は ``pedigree_name``・``surface``・``race_date``・``starts``・``places``。"""
        name = self._name_column
        first_race_day = f"(SELECT min(CAST(race_date AS DATE)) FROM {scope.relation})"
        sql = f"""
        SELECT {name} AS pedigree_name, surface, CAST(race_date AS DATE) AS race_date,
               CAST(count(*) AS INTEGER) AS starts,
               CAST(sum(CASE WHEN finish <= 3 THEN 1 ELSE 0 END) AS INTEGER) AS places
        FROM {facts.FACTS_TABLE}
        WHERE ran AND {name} IS NOT NULL
          AND {name} IN (SELECT {name} FROM {scope.relation})
          AND race_date < (SELECT max(race_date) FROM {scope.relation})
          AND CAST(race_date AS DATE) >= {first_race_day} - {self._window_days}
        GROUP BY ALL
        ORDER BY pedigree_name, surface, race_date
        """
        return self._con.execute(sql).df()
