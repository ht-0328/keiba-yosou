"""対戦レーティング（まとまり O）を作るための、過去の全出走と対象の出走を読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from 共通 import facts

from .target_scope import TargetScope

#: 平地でないレース（対戦レーティングは平地のレースの勝ち負けだけで作る）。
_JUMP = "障害"


class HeadToHeadRunRepository:
    """``first_day`` からの中央の平地の全出走（事実表）と、対象の出走（``scope``）を、1行 = 1頭の出走で読む（1 SQL）。

    対戦レーティングは「同じレースを走った馬どうしの着順の勝ち負け」を開催日の順に積み上げて作るので、対象の出走だけでなく、
    その前の全出走（出走した馬だけ）が要る。過去の出走は、対象のいちばん遅い開催日より前で、対象のレースを除いたもの。
    対象の出走（予測するレース。まだ走っていなくてよい）は ``is_target`` が真で、着順はまだ無ければ欠損値。
    読む列は、レーティングの計算に要るものだけ（レースID・開催日・馬ID・着順）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, first_day: date) -> None:
        self._con = con
        self._first_day = first_day

    def read(self, scope: TargetScope) -> pd.DataFrame:
        """列は ``race_id``・``race_date``（日付型）・``horse_id``・``finish``・``is_target``。開催日・レースID・馬ID の順。"""
        sql = f"""
        WITH target AS (
            SELECT race_id, CAST(race_date AS DATE) AS race_date, horse_id, finish, TRUE AS is_target
            FROM {scope.relation}
            WHERE surface <> '{_JUMP}'
        ), history AS (
            SELECT race_id, CAST(race_date AS DATE) AS race_date, horse_id, finish, FALSE AS is_target
            FROM {facts.FACTS_TABLE}
            WHERE ran AND surface <> '{_JUMP}'
              AND CAST(race_date AS DATE) >= ?
              AND CAST(race_date AS DATE) < (SELECT max(race_date) FROM target)
              AND race_id NOT IN (SELECT DISTINCT race_id FROM target)
        )
        SELECT * FROM history UNION ALL SELECT * FROM target
        ORDER BY race_date, race_id, horse_id
        """
        frame = self._con.execute(sql, [self._first_day.isoformat()]).df()
        return frame.assign(race_date=pd.to_datetime(frame["race_date"]))
