"""競馬場・コース・距離ごとの、全クラスの「前に行った馬」「内枠」の成績（脚質・枠のずれの基準）を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts, keys, stakes


class CourseRateRepository:
    """脚質の前・枠の内の基準になる、コースごとの超過複勝率（3着内率 − 3÷頭数）。

    事実表（``共通/facts.py``）から数えるので、先に ``facts.ensure_facts`` しておく（``loading.load_runners`` がする）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self) -> pd.DataFrame:
        """index が（venue, course, distance_m）、列が ``front_n``・``front_excess``・``inner_excess`` の表。"""
        front_styles = keys.sql_list(stakes.FRONT_STYLES)
        inner = stakes.INNER_FRAME_NO
        return self._con.execute(f"""
        SELECT venue, course, distance_m,
               count(*) FILTER (style IN {front_styles}) AS front_n,
               avg(((finish <= 3)::int) - 3.0 / field_size) FILTER (style IN {front_styles}) AS front_excess,
               avg(((finish <= 3)::int) - 3.0 / field_size) FILTER (frame_no <= {inner}) AS inner_excess
        FROM {facts.FACTS_TABLE} WHERE ran AND surface <> '障害'
        GROUP BY 1, 2, 3
        """).df().set_index(["venue", "course", "distance_m"])
