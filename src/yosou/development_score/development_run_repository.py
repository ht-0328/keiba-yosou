"""表 G の元になる、中央・平地の全出走を読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from 共通 import facts

#: 読む事実表の列（意味は ``tools/共通/facts.py`` の ``FACT_COLUMNS``）。
COLUMNS: tuple[str, ...] = (
    "race_id", "venue_code", "surface", "track_code", "distance_m", "class_order", "field_size",
    "horse_id", "horse_no", "popularity", "win_odds", "finish", "first_corner_rank", "first3f", "last3f_race",
    "win_payout", "place_payout",
)
#: 読み始める開催日（事実表の最初の年。先頭率と前半タイムの基準は、それより前の走から作る）。
FIRST_DAY = date(2011, 1, 1)


class DevelopmentRunRepository:
    """``first_day`` からの中央・平地の全出走（出走した馬だけ。1行 = 1頭）を読む。

    表 G の材料に要る、最初のコーナーの順位（レース前の脚質の元）・前3ハロン（結果のペースの元）・単勝オッズ
    （市場から見た3着以内率の元）・着順と、線を確かめるときに見る人気と払戻を持つ。開催日・レースID・馬番の順に並べる。
    元DB は読むだけ。
    """

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
