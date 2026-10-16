"""対象の馬の過去走を事実表から読む。"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

import duckdb
import pandas as pd

from 共通 import facts

#: 読む事実表の列（意味は ``tools/共通/facts.py`` の ``FACT_COLUMNS``）。
COLUMNS: tuple[str, ...] = (
    "race_id", "race_date", "horse_id", "venue", "race_name", "class_name", "class_order", "grade_code", "surface", "distance_m",
    "condition", "field_size", "frame_no", "popularity", "finish", "time_diff", "first_corner_rank", "corner4", "last3f",
    "last3f_rank", "last3f_count", "jockey", "carried", "body_weight", "weight_change", "interval_days",
)


class PastRunRepository:
    """対象の馬それぞれの、基準日より前の中央の出走（出走取消・除外は飛ばす）を事実表から読む（1 SQL）。

    1行 = 1走。古い走から新しい走の順（馬ごと）。事実表は先に ``facts.ensure_facts`` で作っておく。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, horse_ids: Sequence[str], before: date) -> pd.DataFrame:
        """列は ``COLUMNS``（``race_date`` は日付型、``horse_id`` は文字列）。馬がいなければ空。"""
        if not horse_ids:
            return pd.DataFrame(columns=list(COLUMNS))
        marks = ", ".join("?" for _ in horse_ids)
        sql = f"""
        SELECT {', '.join(COLUMNS)}
        FROM {facts.FACTS_TABLE}
        WHERE horse_id IN ({marks}) AND ran AND CAST(race_date AS DATE) < ?
        ORDER BY horse_id, race_date, race_id
        """
        frame = self._con.execute(sql, [*horse_ids, before.isoformat()]).df()
        return frame.assign(horse_id=frame["horse_id"].astype(str), race_date=pd.to_datetime(frame["race_date"]))
