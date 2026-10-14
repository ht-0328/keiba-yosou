"""登録馬の前走（出走したレース）を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts, keys, stakes

from yosou.shared.repository import TargetScope


class PreviousRunRepository:
    """対象の馬それぞれの、対象のレースの開催日より前の直近の出走（出走取消・除外は飛ばす）を事実表から読む（1 SQL）。

    事実表の ``prev_*`` の列には前走のレース名・クラスが無いので、文に使う分をここで読む。1行 = 1頭（前走の無い馬は行が無い）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, scope: TargetScope) -> pd.DataFrame:
        """列は ``horse_id``・``prev_race_id``・``prev_race_date``・``prev_race_name``・``prev_class_name``・``prev_grade_code``・
        ``prev_stakes_no``（前走が重賞ならその特別競走番号。重賞の対応表 ``stakes_map`` が要る）・``prev_venue``・``prev_surface``・
        ``prev_distance_m``・``prev_finish``・``prev_popularity``・``prev_time_diff``・``prev_field_size``。"""
        sql = f"""
        WITH target AS (
            SELECT DISTINCT horse_id, CAST(race_date AS DATE) AS race_date FROM {scope.relation}
        ), runs AS (
            SELECT f.horse_id, f.race_id AS prev_race_id, CAST(f.race_date AS DATE) AS prev_race_date,
                   f.race_name AS prev_race_name, f.class_name AS prev_class_name, trim(f.grade_code) AS prev_grade_code,
                   f.venue AS prev_venue, f.surface AS prev_surface, f.distance_m AS prev_distance_m,
                   f.finish AS prev_finish, f.popularity AS prev_popularity, f.time_diff AS prev_time_diff, f.field_size AS prev_field_size,
                   m.stakes_no AS prev_stakes_no,
                   row_number() OVER (PARTITION BY f.horse_id ORDER BY f.race_date DESC, f.race_id DESC) AS n
            FROM {facts.FACTS_TABLE} f
            JOIN target t ON t.horse_id = f.horse_id AND CAST(f.race_date AS DATE) < t.race_date
            LEFT JOIN {keys.q(stakes.STAKES_MAP_TABLE)} m ON m.race_id = f.race_id
            WHERE f.ran
        )
        SELECT * EXCLUDE (n) FROM runs WHERE n = 1 ORDER BY horse_id
        """
        frame = self._con.execute(sql).df()
        return frame.assign(horse_id=frame["horse_id"].astype(str), prev_race_date=pd.to_datetime(frame["prev_race_date"]))
