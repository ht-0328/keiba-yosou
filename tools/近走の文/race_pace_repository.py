"""レースのペースを読む。"""

from __future__ import annotations

from collections.abc import Sequence

import duckdb
import pandas as pd

from 共通 import facts

#: 基準を作るのに要る、それより前の同じ条件（競馬場・芝ダ・距離・馬場状態）のレースの数（馬の力の材料の ``RacePace`` と同じ）。
MIN_RACES = 20


class RacePaceRepository:
    """レースの前半の速さ（ペース）を、前3F を同じ競馬場・芝ダ・距離・馬場状態の、それより前のレースの平均と標準偏差で z にして読む（1 SQL）。

    正ならハイ、負ならスロー。基準はそのレースより前のレースだけで作る（同じ日は race_id の順に前とみなす）。
    前の同じ条件のレースが ``MIN_RACES`` より少なければ欠損値。馬の力の材料の ``RacePace`` と同じ決まりを SQL で引く。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, race_ids: Sequence[str]) -> pd.Series:
        """race_id → ペース（z。基準が足りなければ NaN）。"""
        if not race_ids:
            return pd.Series(dtype=float)
        marks = ", ".join("?" for _ in race_ids)
        sql = f"""
        WITH races AS (
            SELECT race_id, CAST(any_value(race_date) AS DATE) AS race_date, any_value(venue_code) AS venue_code,
                   any_value(surface) AS surface, any_value(distance_m) AS distance_m, any_value(condition) AS condition,
                   TRY_CAST(any_value(first3f) AS DOUBLE) AS first3f
            FROM {facts.FACTS_TABLE}
            GROUP BY race_id
        ), target AS (
            SELECT * FROM races WHERE race_id IN ({marks})
        )
        SELECT t.race_id, t.first3f, avg(r.first3f) AS mean, stddev_pop(r.first3f) AS std, count(r.first3f) AS n
        FROM target t
        LEFT JOIN races r
          ON r.venue_code = t.venue_code AND r.surface = t.surface AND r.distance_m = t.distance_m AND r.condition = t.condition
         AND r.first3f IS NOT NULL AND (r.race_date < t.race_date OR (r.race_date = t.race_date AND r.race_id < t.race_id))
        GROUP BY t.race_id, t.first3f
        """
        frame = self._con.execute(sql, list(race_ids)).df()
        enough = (frame["n"] >= MIN_RACES) & frame["first3f"].notna()
        pace = -(frame["first3f"] - frame["mean"]) / frame["std"].clip(lower=1e-6)
        return pd.Series(pace.where(enough).to_numpy(dtype=float), index=frame["race_id"].astype(str).to_numpy())
