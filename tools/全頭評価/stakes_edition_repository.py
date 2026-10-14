"""重賞の過去の開催の出走馬を読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from 共通 import facts, keys, stakes


class StakesEditionRepository:
    """同じ重賞（特別競走番号）の、その開催日より前の開催の出走馬を読む（1 SQL）。1行 = 1頭の出走。

    列は 出走の同定（``race_id``・``race_date``・``horse_id``）、結果（``finish``・``popularity``・``win_payout``・``place_payout``・``field_size``）、
    条件（``prev_race_name``・``prev_class_name``・``prev_stakes_no``・``prev_popularity``・``interval_days``・``affiliation``・``same_race_places_before``）。
    前走のレース名と特別競走番号（重賞なら）は事実表に無いので、その馬の直前の出走から引く。傾向の文（``StakesTendencyPoints``）の材料。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, stakes_no: str, before: date) -> pd.DataFrame:
        sql = f"""
        WITH editions AS (
            SELECT race_id, CAST(race_date AS DATE) AS race_date
            FROM {keys.q(stakes.STAKES_MAP_TABLE)}
            WHERE stakes_no = ? AND CAST(race_date AS DATE) < ?
        ), runners AS (
            SELECT f.race_id, e.race_date, f.horse_id, f.finish, f.popularity, f.prev_popularity, f.interval_days, f.affiliation,
                   f.same_race_places_before, f.win_payout, f.place_payout, f.field_size
            FROM {facts.FACTS_TABLE} f
            JOIN editions e USING (race_id)
            WHERE f.ran
        )
        SELECT r.*, p.race_name AS prev_race_name, p.class_name AS prev_class_name, p.stakes_no AS prev_stakes_no
        FROM runners r
        LEFT JOIN LATERAL (
            SELECT p.race_name, p.class_name, m.stakes_no FROM {facts.FACTS_TABLE} p
            LEFT JOIN {keys.q(stakes.STAKES_MAP_TABLE)} m ON m.race_id = p.race_id
            WHERE p.horse_id = r.horse_id AND p.ran AND CAST(p.race_date AS DATE) < r.race_date
            ORDER BY p.race_date DESC, p.race_id DESC LIMIT 1
        ) p ON TRUE
        ORDER BY r.race_date, r.race_id, r.horse_id
        """
        frame = self._con.execute(sql, [stakes_no, before.isoformat()]).df()
        return frame.assign(race_date=pd.to_datetime(frame["race_date"]), horse_id=frame["horse_id"].astype(str))
