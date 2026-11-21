"""事実表から、高知で出走した馬の行を読む（1 SQL）。"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import pandas as pd

from 共通.facts import FACTS_TABLE, ensure_facts

#: 高知の競馬場名（事実表の ``venue``）。
VENUE = "高知"
#: 読む列（事実表の列名）。結果側の列（着順・着差・通過順・払戻）は、過去走の材料と、当たり外れを数えるために使う。
COLUMNS: tuple[str, ...] = (
    "race_id", "race_date", "race_no", "race_name", "class_name", "class_order", "distance_m", "condition", "field_size",
    "frame_no", "horse_no", "horse_id", "sex", "age", "jockey_code", "carried", "weight_change", "popularity", "win_odds",
    "finish", "time_diff", "corner4", "first_corner_rank", "last3f_rank", "win_payout", "place_payout",
    "prev_finish", "prev_time_diff", "prev_corner4", "interval_days", "jockey_change", "apprentice", "best_time_unit_rank",
)


@dataclass(frozen=True)
class KochiRunsRepository:
    """高知の全レースの出走の行（事実表の ``ran`` が真のもの。ファイナルレース以外も含む）。"""

    con: duckdb.DuckDBPyConnection

    def load(self) -> pd.DataFrame:
        ensure_facts(self.con)
        columns = ", ".join(COLUMNS)
        sql = f"SELECT {columns} FROM {FACTS_TABLE} WHERE ran AND venue = ? ORDER BY race_id, horse_no"
        return self.con.execute(sql, [VENUE]).df()
