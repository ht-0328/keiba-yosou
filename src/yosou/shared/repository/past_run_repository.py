"""過去走を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts

from .target_scope import TargetScope


class PastRunRepository:
    """対象の馬が中央で出走した、過去のレースを読む（1行 = 1走。出走しなかった行は入れない）。

    読むのは、対象のいちばん遅い開催日より前の走。どの走を使うかは、特徴量を作る側が出走ごとの開催日で決める。
    単勝人気は、近走の人気を特徴量にする予想（人気馬が4着以下になるかの予想）のために読む。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, scope: TargetScope) -> pd.DataFrame:
        """馬・開催日の古い順に並べる。"""
        sql = f"""
        SELECT horse_id, CAST(race_date AS DATE) AS race_date, race_id,
               finish, time_diff, last3f_rank, corner4, field_size, popularity
        FROM {facts.FACTS_TABLE}
        WHERE ran
          AND horse_id IN (SELECT horse_id FROM {scope.relation})
          AND race_date < (SELECT max(race_date) FROM {scope.relation})
        ORDER BY horse_id, race_date, race_id
        """
        return self._con.execute(sql).df()
