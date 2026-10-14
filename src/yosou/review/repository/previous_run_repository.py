"""これから走る馬の、前走と前々走（中央・平地）を読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from 共通 import facts

#: 読む走の数（前走と前々走）。
RUNS = 2


class PreviousRunRepository:
    """事実表から、``horse_ids`` の馬の ``before``（開催日）より前の中央・平地の走を、新しい順に最大2つ読む。

    予測のときに、保存した馬の回顧ノート（表3）を引く鍵（レースID・馬ID）を知るため。元DB は読むだけ。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, horse_ids: list[str], before: date) -> pd.DataFrame:
        """列は ``horse_id``・``race_id``・``race_date``（日付型）・``runs_ago``（1 が前走）。"""
        if not horse_ids:
            return pd.DataFrame(columns=["horse_id", "race_id", "race_date", "runs_ago"])
        facts.ensure_facts(self._con)
        placeholders = ", ".join("?" for _ in horse_ids)
        sql = f"""
        SELECT horse_id, race_id, CAST(race_date AS DATE) AS race_date, runs_ago FROM (
            SELECT horse_id, race_id, race_date,
                   row_number() OVER (PARTITION BY horse_id ORDER BY race_date DESC, race_id DESC) AS runs_ago
            FROM {facts.FACTS_TABLE}
            WHERE ran AND surface IN ('芝', 'ダート') AND CAST(race_date AS DATE) < ? AND horse_id IN ({placeholders})
        ) WHERE runs_ago <= {RUNS}
        ORDER BY horse_id, runs_ago
        """
        frame = self._con.execute(sql, [before.isoformat(), *horse_ids]).df()
        return frame.assign(horse_id=frame["horse_id"].astype(str), race_id=frame["race_id"].astype(str), race_date=pd.to_datetime(frame["race_date"]))
