"""材料の実験に使う、全出走の列を読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from 共通 import facts

#: 読む事実表の列（意味は ``tools/共通/facts.py`` の ``FACT_COLUMNS``）。
_COLUMNS: tuple[str, ...] = (
    "race_id", "venue_code", "surface", "distance_m", "condition_code", "class_order", "race_no", "field_size",
    "horse_id", "horse_no", "finish", "finish_time", "corner4", "win_odds", "popularity",
    "jockey_code", "trainer_code", "sire", "damsire",
)


class RunnerHistoryRepository:
    """``first_day`` からの中央・平地の全出走（出走した馬だけ。1行 = 1頭）を、材料の実験に使う列で読む。

    能力指数（走破タイム）・当日の馬場傾向（4角の位置と馬番）・過去の市場に対する成績（オッズと着順）・
    騎手と調教師と血統の市場に対する成績、の材料になる。開催日・レースID・馬番の順に並べる。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, first_day: date) -> pd.DataFrame:
        facts.ensure_facts(self._con)
        sql = f"""
        SELECT {", ".join(_COLUMNS)}, CAST(race_date AS DATE) AS race_date
        FROM {facts.FACTS_TABLE}
        WHERE ran AND surface <> '障害' AND CAST(race_date AS DATE) >= ?
        ORDER BY race_date, race_id, horse_no
        """
        frame = self._con.execute(sql, [first_day.isoformat()]).df()
        return frame.assign(race_date=pd.to_datetime(frame["race_date"]))
