"""事実表から、係数の当てはめに使う出走の行（レース・馬番・枠番・人気・単勝オッズ・確定着順）を読む（1 SQL）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import duckdb
import pandas as pd

from 共通.facts import ensure_facts

COLUMNS: tuple[str, ...] = ("race_id", "race_date", "field_size", "frame_no", "horse_no", "popularity", "win_odds", "finish")


@dataclass(frozen=True)
class FactsRowsRepository:
    """``date_from`` 以降で出走頭数が ``min_heads`` 以上のレースの、出走した馬の行（事実表の ``ran`` が真のもの）。``race_id`` は 16桁の文字列。"""

    con: duckdb.DuckDBPyConnection

    def load(self, date_from: date, min_heads: int) -> pd.DataFrame:
        table = ensure_facts(self.con)
        sql = f"SELECT {', '.join(COLUMNS)} FROM {table} WHERE ran AND race_date >= ? AND field_size >= ? ORDER BY race_id, horse_no"
        return self.con.execute(sql, [date_from.isoformat(), min_heads]).df()
