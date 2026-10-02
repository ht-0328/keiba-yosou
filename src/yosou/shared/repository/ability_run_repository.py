"""馬の力の材料（まとまり M）を作るための、過去の全出走と対象の出走を読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from 共通 import facts, keys

from .target_scope import TargetScope

#: 読む事実表の列（意味は ``tools/共通/facts.py`` の ``FACT_COLUMNS``）。開催日は日付型にして別に足す。
RUN_COLUMNS: tuple[str, ...] = (
    "race_id", "horse_id", "horse_no", "frame_no", "ran", "finish", "field_size", "time_diff",
    "first_corner_rank", "corner4", "last3f_rank", "last3f_count", "first3f", "class_order", "carried",
    "interval_days", "body_weight", "weight_change", "venue_code", "surface", "distance_m", "condition",
    "condition_order", "surface_order", "sex_order", "age", "month", "jockey_code", "trainer_code", "sire", "damsire",
    "weight_type", "affiliation", "blinker", "apprentice", "runs_before", "wins_before", "lead_runs_before",
    "course_runs_before", "course_wins_before", "course_places_before", "venue_wins_before", "dist_wins_before",
    "cond_places_before", "same_race_runs_before", "same_race_wins_before", "best_time_unit_rank",
    "best_time_dist_rank",
)
#: 馬主・生産者・母を読む表の列（表が無い DB では空の関係にする）。
_SE_COLUMNS = (*keys.RACE_KEY, keys.HORSE_KEY, "馬主コード")
_UM_COLUMNS = (keys.HORSE_KEY, "馬主コード", "生産者コード")
_SK_COLUMNS = (keys.HORSE_KEY, "生産者コード", "3代血統 繁殖登録番号_02")


class AbilityRunRepository:
    """``first_day`` からの中央の全出走（事実表）と、対象の出走（``scope``）を、1行 = 1頭の出走で読む（1 SQL）。

    馬の力の材料は、馬ごとの近走・騎手や馬主ごとの通算の成績・過去のレースの強さとペースから作るので、対象の出走だけでなく
    その前の全出走が要る。過去の出走は、対象のいちばん遅い開催日より前で、対象のレースを除いたもの。
    対象の出走（予測するレース。まだ走っていなくてよい）は ``is_target`` が真。
    馬主は、その出走の馬毎レース情報の馬主コード（木曜など、まだ無ければ競走馬マスタの今の馬主コード）。
    生産者と母（繁殖登録番号）は、産駒マスタ（無ければ競走馬マスタの生産者コード）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, first_day: date) -> None:
        self._con = con
        self._first_day = first_day

    def read(self, scope: TargetScope) -> pd.DataFrame:
        """列は ``RUN_COLUMNS``・``race_date``（日付型）・``is_target``・``owner``・``breeder``・``dam``。"""
        columns = ", ".join(RUN_COLUMNS)
        horse = keys.q(keys.HORSE_KEY)
        se = facts.optional_relation(self._con, "se", _SE_COLUMNS)
        um = facts.optional_relation(self._con, "um", _UM_COLUMNS)
        sk = facts.optional_relation(self._con, "sk", _SK_COLUMNS)
        sql = f"""
        WITH target AS (
            SELECT {columns}, CAST(race_date AS DATE) AS race_date, TRUE AS is_target FROM {scope.relation}
        ), history AS (
            SELECT {columns}, CAST(race_date AS DATE) AS race_date, FALSE AS is_target FROM {facts.FACTS_TABLE}
            WHERE CAST(race_date AS DATE) >= ?
              AND CAST(race_date AS DATE) < (SELECT max(race_date) FROM target)
              AND race_id NOT IN (SELECT DISTINCT race_id FROM target)
        ), runs AS (
            SELECT * FROM history UNION ALL SELECT * FROM target
        ), race_owner AS (
            SELECT {keys.rid_expr('s')} AS race_id, s.{horse} AS horse_id, any_value(s."馬主コード") AS owner
            FROM {se} AS s
            WHERE {keys.jra_only('s')} AND nullif(trim(s."馬主コード"), '') IS NOT NULL
            GROUP BY ALL
        ), horse_master AS (
            SELECT {horse} AS horse_id, any_value(nullif(trim("馬主コード"), '')) AS owner,
                   any_value(nullif(trim("生産者コード"), '')) AS breeder
            FROM {um} GROUP BY ALL
        ), parents AS (
            SELECT {horse} AS horse_id, any_value(nullif(trim("生産者コード"), '')) AS breeder,
                   any_value(nullif(trim("3代血統 繁殖登録番号_02"), '')) AS dam
            FROM {sk} GROUP BY ALL
        )
        SELECT runs.*, coalesce(race_owner.owner, horse_master.owner) AS owner,
               coalesce(parents.breeder, horse_master.breeder) AS breeder, parents.dam AS dam
        FROM runs
        LEFT JOIN race_owner ON race_owner.race_id = runs.race_id AND race_owner.horse_id = runs.horse_id
        LEFT JOIN horse_master ON horse_master.horse_id = runs.horse_id
        LEFT JOIN parents ON parents.horse_id = runs.horse_id
        ORDER BY runs.race_date, runs.race_id, runs.horse_no, runs.horse_id
        """
        frame = self._con.execute(sql, [self._first_day.isoformat()]).df()
        return frame.assign(race_date=pd.to_datetime(frame["race_date"]))
