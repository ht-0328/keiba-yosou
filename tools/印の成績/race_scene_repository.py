"""レースの場面（クラス・競馬場・芝ダ・距離・頭数）を事実表から読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts

#: 読むレースIDを入れる一時表。
_WANTED = "mark_stats_scene_races"
#: 読む列（事実表の列。1レースで同じ値）。
COLUMNS: tuple[str, ...] = ("venue", "surface", "distance_m", "class_name", "class_order", "field_size")


class RaceSceneRepository:
    """``race_ids`` のレースの場面を、事実表（``tools/共通/facts.py``）から1レース1行で読む
    （研究「回収率100超の施策」の施策4。場面ごとに上乗せと回収率を測る）。

    列は race_id と ``COLUMNS``（競馬場の名前・芝ダ・距離・クラス名・クラスの並び順・出走頭数）。
    """

    def read(self, con: duckdb.DuckDBPyConnection, race_ids: pd.Series) -> pd.DataFrame:
        table = facts.ensure_facts(con)
        con.register("mark_stats_scene_race_ids", pd.DataFrame({"race_id": race_ids.astype(str).drop_duplicates()}))
        con.execute(f"CREATE OR REPLACE TEMP TABLE {_WANTED} AS SELECT * FROM mark_stats_scene_race_ids")
        picked = ", ".join(f"any_value(f.{column}) AS {column}" for column in COLUMNS)
        sql = f"""
            SELECT f.race_id, {picked}
            FROM {table} AS f JOIN {_WANTED} USING (race_id)
            GROUP BY f.race_id
        """
        return con.execute(sql).df().astype({"race_id": str})
