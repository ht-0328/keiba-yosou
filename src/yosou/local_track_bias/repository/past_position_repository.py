"""これから走る1レースの出走馬の、直近3走の4コーナーの位置の平均を事実表から読む。"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

import duckdb
import pandas as pd

from 共通 import facts

from ..front_position import FRONT_POSITION, RECENT_RUNS


class PastPositionRepository:
    """``before`` より前の出走のうち、馬ごとに新しい順に ``RECENT_RUNS`` 走（4コーナーの順位のある出走だけ）の
    位置（（順位 − 1）÷（頭数 − 1））の平均を読む。学習データの ``FrontPosition`` と同じ決めごとである。

    元DB は読むだけ。直近の走が無い馬は表に出ない（呼ぶ側が欠損値にする）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, before: date, horse_ids: Sequence[str]) -> pd.DataFrame:
        """1行 = 1頭。列は ``horse_id``・``corner4_pred``。"""
        ids = [str(horse_id) for horse_id in horse_ids]
        if not ids:
            return pd.DataFrame({"horse_id": pd.Series(dtype=str), FRONT_POSITION: pd.Series(dtype="float64")})
        facts.ensure_facts(self._con)
        placeholders = ", ".join("?" for _ in ids)
        sql = f"""
        WITH runs AS (
            SELECT horse_id, (corner4 - 1.0) / (field_size - 1) AS position,
                   row_number() OVER (PARTITION BY horse_id ORDER BY race_date DESC, race_id DESC) AS recency
            FROM {facts.FACTS_TABLE}
            WHERE ran AND corner4 IS NOT NULL AND field_size > 1 AND CAST(race_date AS DATE) < ? AND horse_id IN ({placeholders})
        )
        SELECT horse_id, avg(position) AS {FRONT_POSITION} FROM runs WHERE recency <= {RECENT_RUNS} GROUP BY horse_id ORDER BY horse_id
        """
        frame = self._con.execute(sql, [before.isoformat(), *ids]).df()
        return frame.astype({"horse_id": str, FRONT_POSITION: "float64"})
