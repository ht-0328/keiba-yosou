"""回顧の元になる、中央・平地の全出走を読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from 共通 import facts

#: 読む事実表の列（意味は ``tools/共通/facts.py`` の ``FACT_COLUMNS``）。表 G の材料（展開スコア）・傾きの材料（トラックバイアス）・
#: 不利の判定（最初のコーナーの順位・4コーナーの順位・着順）と、枠連の買い目の精算（枠番）に要る列をそろえる。
COLUMNS: tuple[str, ...] = (
    "race_id", "venue_code", "surface", "track_code", "condition_code", "race_no", "distance_m", "class_order", "field_size",
    "horse_id", "horse_no", "frame_no", "popularity", "win_odds", "finish", "first_corner_rank", "corner4", "first3f", "last3f_race",
    "win_payout", "place_payout",
)
#: 読み始める開催日（事実表の最初の年）。
FIRST_DAY = date(2011, 1, 1)


class ReviewRunRepository:
    """``first_day`` からの中央・平地の全出走（出走した馬だけ。1行 = 1頭）を読む。その日の終わったレース（速報の成績）も含む。
    開催日・レースID・馬番の順。元DB は読むだけ。"""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, first_day: date = FIRST_DAY) -> pd.DataFrame:
        """列は ``COLUMNS`` と ``race_date``（日付型）。"""
        facts.ensure_facts(self._con)
        sql = f"""
        SELECT {", ".join(COLUMNS)}, CAST(race_date AS DATE) AS race_date
        FROM {facts.FACTS_TABLE}
        WHERE ran AND surface IN ('芝', 'ダート') AND CAST(race_date AS DATE) >= ?
        ORDER BY race_date, race_id, horse_no
        """
        frame = self._con.execute(sql, [first_day.isoformat()]).df()
        return frame.assign(race_date=pd.to_datetime(frame["race_date"]))
