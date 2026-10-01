"""出走ごとに、レースの前の調教（坂路・ウッド）をまとめた値を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts, keys

from .target_scope import TargetScope

#: 調教のタイムは 0.1秒単位の文字列（例: '0528' は 52.8秒）。0 は記録なし。
_SECONDS = "nullif(try_cast({column} as double), 0) / 10.0"
_HILL_COLUMNS = (keys.HORSE_KEY, "調教年月日", "4ハロンタイム合計(800M～0M)", "ラップタイム(200M～0M)")
_WOOD_COLUMNS = (keys.HORSE_KEY, "調教年月日", "5ハロンタイム合計(1000M～0M)", "4ハロンタイム合計(800M～0M)",
                 "ラップタイム(200M～0M)")


class WorkoutSummaryRepository:
    """対象の出走それぞれの、レースの前日までの 14日・30日の調教をまとめた値を読む（1 SQL）。

    馬の力の材料（研究「馬の力と展開でオッズに勝つ」の調教の材料）。坂路は本数・最速の4ハロンとラスト1ハロン・直前の1本、
    ウッドは本数・最速の5ハロン・4ハロン・ラスト1ハロン・直前の1本のラスト1ハロン。調教の無い出走は欠損値（本数も）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, scope: TargetScope) -> pd.DataFrame:
        """1行 = 対象の出走1頭。列は ``race_id``・``horse_id`` と、馬の力の材料の調教の12列（``WORKOUT_COLUMNS``）。"""
        hill = facts.optional_relation(self._con, "hc", _HILL_COLUMNS)
        wood = facts.optional_relation(self._con, "wc", _WOOD_COLUMNS)
        horse = keys.q(keys.HORSE_KEY)
        sql = f"""
        WITH runs AS (
            SELECT DISTINCT race_id, horse_id, CAST(race_date AS DATE) AS race_date FROM {scope.relation}
        ), hill AS (
            SELECT {horse} AS horse_id, try_strptime("調教年月日", '%Y%m%d')::date AS day,
                   {_SECONDS.format(column='"4ハロンタイム合計(800M～0M)"')} AS f4,
                   {_SECONDS.format(column='"ラップタイム(200M～0M)"')} AS f1
            FROM {hill}
        ), wood AS (
            SELECT {horse} AS horse_id, try_strptime("調教年月日", '%Y%m%d')::date AS day,
                   {_SECONDS.format(column='"5ハロンタイム合計(1000M～0M)"')} AS f5,
                   {_SECONDS.format(column='"4ハロンタイム合計(800M～0M)"')} AS f4,
                   {_SECONDS.format(column='"ラップタイム(200M～0M)"')} AS f1
            FROM {wood}
        ), hill_summary AS (
            SELECT runs.race_id, runs.horse_id,
                   count(*) FILTER (WHERE hill.day >= runs.race_date - 14) AS "坂路_本数14日",
                   count(*) AS "坂路_本数30日",
                   min(hill.f4) FILTER (WHERE hill.day >= runs.race_date - 14) AS "坂路_4F最速14日",
                   min(hill.f1) FILTER (WHERE hill.day >= runs.race_date - 14) AS "坂路_1F最速14日",
                   arg_max(hill.f4, hill.day) AS "坂路_直前4F", arg_max(hill.f1, hill.day) AS "坂路_直前1F",
                   min(runs.race_date - hill.day) AS "坂路_直前からの日数"
            FROM runs JOIN hill ON hill.horse_id = runs.horse_id
             AND hill.day BETWEEN runs.race_date - 30 AND runs.race_date - 1
            GROUP BY ALL
        ), wood_summary AS (
            SELECT runs.race_id, runs.horse_id,
                   count(*) AS "ウッド_本数30日",
                   min(wood.f5) AS "ウッド_5F最速30日", min(wood.f4) AS "ウッド_4F最速30日",
                   min(wood.f1) AS "ウッド_1F最速30日", arg_max(wood.f1, wood.day) AS "ウッド_直前1F"
            FROM runs JOIN wood ON wood.horse_id = runs.horse_id
             AND wood.day BETWEEN runs.race_date - 30 AND runs.race_date - 1
            GROUP BY ALL
        )
        SELECT runs.race_id, runs.horse_id,
               hill_summary.* EXCLUDE (race_id, horse_id), wood_summary.* EXCLUDE (race_id, horse_id)
        FROM runs
        LEFT JOIN hill_summary ON hill_summary.race_id = runs.race_id AND hill_summary.horse_id = runs.horse_id
        LEFT JOIN wood_summary ON wood_summary.race_id = runs.race_id AND wood_summary.horse_id = runs.horse_id
        """
        return self._con.execute(sql).df()
