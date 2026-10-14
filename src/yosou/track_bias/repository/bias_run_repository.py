"""トラックバイアスの元になる、中央・平地の全出走を読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from 共通 import facts

from .. import names

#: 読む事実表の列（意味は ``tools/共通/facts.py`` の ``FACT_COLUMNS``）。
COLUMNS: tuple[str, ...] = (
    names.RACE_ID, names.VENUE_CODE, names.SURFACE, names.TRACK_CODE, names.CONDITION_CODE, names.RACE_NO, "field_size",
    "horse_id", "horse_no", "corner4", "finish", "win_odds",
)
#: 読み始める開催日（事実表の最初の年）。
FIRST_DAY = date(2011, 1, 1)


class BiasRunRepository:
    """``first_day`` からの中央・平地の全出走（出走した馬だけ。1行 = 1頭）を読む。

    傾きに要る、馬番と頭数（内らしさの元）・4コーナーの順位（前らしさの元）・単勝オッズ（市場から見た3着以内率の元）・着順を持つ。
    その日の終わったレース（速報の成績。事実表に入る）も含むので、当日の先に終わったレースの材料にもなる。開催日・レースID・馬番の順に並べる。
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
