"""展開の理論を確かめるのに使う、全出走の列を読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from 共通 import facts

#: 読む事実表の列（意味は ``tools/共通/facts.py`` の ``FACT_COLUMNS``）。
COLUMNS: tuple[str, ...] = (
    "race_id", "year", "venue_code", "venue", "race_no", "race_name", "track_code", "surface", "course", "distance_m",
    "condition", "class_name", "class_order", "grade_code", "field_size",
    "horse_id", "horse_no", "popularity", "win_odds", "finish", "time_diff",
    "style", "style_before", "lead_candidates", "first_corner_rank", "corner4", "last3f", "first3f", "last3f_race",
    "win_payout", "place_payout",
)


class PaceRunnerRepository:
    """``first_day`` からの中央・平地の全出走（出走した馬だけ。1行 = 1頭）を読む。

    レースの前半・後半のタイム（``first3f``・``last3f_race``）、結果の脚質と推定脚質、着順と払戻を持つ。
    開催日・レースID・馬番の順に並べる。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, first_day: date) -> pd.DataFrame:
        facts.ensure_facts(self._con)
        sql = f"""
        SELECT {", ".join(COLUMNS)}, CAST(race_date AS DATE) AS race_date
        FROM {facts.FACTS_TABLE}
        WHERE ran AND surface IN ('芝', 'ダート') AND CAST(race_date AS DATE) >= ?
        ORDER BY race_date, race_id, horse_no
        """
        frame = self._con.execute(sql, [first_day.isoformat()]).df()
        return frame.assign(race_date=pd.to_datetime(frame["race_date"]))
