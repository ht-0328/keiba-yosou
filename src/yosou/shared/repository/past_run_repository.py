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
    最初のコーナーの順位・上がり3ハロン・レースの後3ハロンなどは、展開から着順を予想する予想が、序盤と末脚の履歴を作るために読む。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, scope: TargetScope) -> pd.DataFrame:
        """馬・開催日の古い順に並べる。"""
        sql = f"""
        SELECT horse_id, CAST(race_date AS DATE) AS race_date, race_id,
               finish, time_diff, last3f_rank, corner4, field_size, popularity,
               horse_no, venue_code, track_code, surface, distance_m,
               first_corner_no, corner_laps_over_one, first_corner_rank,
               last3f, last3f_count, last3f_race
        FROM {facts.FACTS_TABLE}
        WHERE ran
          AND horse_id IN (SELECT horse_id FROM {scope.relation})
          AND race_date < (SELECT max(race_date) FROM {scope.relation})
        ORDER BY horse_id, race_date, race_id
        """
        return self._con.execute(sql).df()
