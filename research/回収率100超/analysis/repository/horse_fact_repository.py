"""事実表から、馬の実力を表す列を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts

#: 事実表から持ってくる列。すべてレース前に分かるもの。
FACT_COLUMNS: tuple[str, ...] = (
    "race_id", "horse_no", "race_date", "race_no", "field_size",
    "frame_no", "age", "carried", "body_weight", "weight_change", "distance_m", "class_order",
    "jockey_code", "trainer_code", "sire", "damsire",
    "prev_finish", "prev_popularity", "interval_days", "prev_last3f", "prev_last3f_rank",
    "prev_time_diff", "prev_corner4", "prev_field_size", "prev_distance_m",
    "runs_before", "wins_before", "lead_runs_before", "course_runs_before", "course_wins_before",
    "best_time_unit", "best_time_unit_rank", "best_time_dist", "best_time_dist_rank",
)


class HorseFactRepository:
    """事実表（``tools/共通/facts.py``）から、馬の実力に関する列を読む。

    前走・持ち時計・出走数など、レース前に分かる値だけを取る。同じ定義を2か所に書かないよう、
    事実表の SQL をそのまま使う。

    騎手・調教師・血統のコードも取るが、モデルにはそのまま渡さない。
    渡すと名前を覚えるだけになり、新しい年で当たらなくなった（実測）。
    ``MarketExcessRate`` で「市場の期待に対する超過成績」の数値に変えてから使う。
    """

    def __init__(self, connection: duckdb.DuckDBPyConnection, first_year: int = 2016) -> None:
        self._connection = connection
        self._first_year = first_year

    def read(self) -> pd.DataFrame:
        """1行 = 1頭の出走。``rid`` と ``horse_no`` で出走の表とつながる。"""
        facts.ensure_facts(self._connection)
        available = {row[0] for row in self._connection.execute("describe facts").fetchall()}
        columns = [column for column in FACT_COLUMNS if column in available]
        sql = (f"select {', '.join(columns)} from facts "
               f"where ran and race_date >= '{self._first_year}-01-01'")
        return self._connection.execute(sql).fetch_df().rename(columns={"race_id": "rid"})
