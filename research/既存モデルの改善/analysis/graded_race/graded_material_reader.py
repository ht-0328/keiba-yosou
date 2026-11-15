"""まとまり W（重賞の格と実績）の材料を、元DB の事実表から読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from 共通 import facts, stakes

#: 平地の重賞のグレードコード（G1・G2・G3）。
_GRADED = "('A', 'B', 'C')"
#: クラス名 → 格の名前（設計書 06 の図3）。グレードの無い重賞（D）は G3 と同じ段にする。
_GRADE_NAME_SQL = """CASE WHEN {surface} = '障害' THEN '障害'
                         WHEN {cls} IN ('G1', 'G2', 'G3', 'L') THEN {cls}
                         WHEN {cls} = '重賞' THEN 'G3'
                         WHEN {cls} = 'オープン' THEN 'OP'
                         ELSE '条件' END"""


class GradedMaterialReader:
    """対象（中央の平地の出走。``first_day`` 以降）ごとに、W の14個を1本の SQL で読む（1行 = 1頭の出走）。

    実績は、その馬の開催日より前の中央の出走だけから数える（同じ日の先のレースも数えない。設計書 11）。
    数えるのは DB にある出走（2011年から）。同じ重賞（特別競走番号）の経験は、重賞でない行では欠損値。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, first_day: date) -> pd.DataFrame:
        facts.ensure_facts(self._con)
        stakes_map = stakes.ensure_stakes_map(self._con)
        frame = self._con.execute(self._sql(stakes_map), [first_day.isoformat()]).df()
        return frame.assign(race_id=frame["race_id"].astype(str), horse_id=frame["horse_id"].astype(str))

    def _sql(self, stakes_map: str) -> str:
        grade_now = _GRADE_NAME_SQL.format(surface="t.surface", cls="t.class_name")
        grade_prev = _GRADE_NAME_SQL.format(surface="struct_extract(t.prev, 'surface')", cls="struct_extract(t.prev, 'cls')")
        return f"""
        WITH f AS (
            SELECT race_id, race_date, horse_id, surface, grade_code, class_name, class_order, weight_type, carried, finish, ran
            FROM {facts.FACTS_TABLE}
        ),
        t AS (
            SELECT f.*,
                   max(carried) OVER (PARTITION BY race_id) AS top_carried,
                   lag(CASE WHEN ran THEN struct_pack(cls := class_name, surface := surface) END IGNORE NULLS)
                       OVER (PARTITION BY horse_id ORDER BY race_date, race_id) AS prev
            FROM f
        ),
        target AS (
            SELECT t.*, m.stakes_no FROM t LEFT JOIN {stakes_map} m ON m.race_id = t.race_id AND t.grade_code IN {_GRADED}
            WHERE t.race_date >= ? AND t.surface <> '障害'
        ),
        career AS (
            SELECT g.race_id, g.horse_id,
                   count(*) FILTER (WHERE p.grade_code IN {_GRADED}) AS graded_runs,
                   count(*) FILTER (WHERE p.grade_code IN {_GRADED} AND p.finish <= 3) AS graded_top3,
                   count(*) FILTER (WHERE p.grade_code IN {_GRADED} AND p.finish = 1) AS graded_wins,
                   count(*) FILTER (WHERE p.grade_code = 'A' AND p.finish <= 3) AS g1_top3,
                   count(*) FILTER (WHERE p.surface <> '障害' AND p.class_order <= 10 AND p.class_order >= g.class_order
                                    AND p.finish <= 3) AS step_top3,
                   arg_max(p.finish, p.race_date) FILTER (WHERE p.grade_code IN {_GRADED}) AS last_graded_finish
            FROM target g JOIN f p ON p.horse_id = g.horse_id AND p.race_date < g.race_date AND p.ran
            GROUP BY g.race_id, g.horse_id
        ),
        editions AS (
            SELECT f.race_id, f.race_date, f.horse_id, f.finish, f.ran, m.stakes_no
            FROM f JOIN {stakes_map} m USING (race_id)
        ),
        same_stakes AS (
            SELECT g.race_id, g.horse_id,
                   count(e.race_id) FILTER (WHERE e.ran) AS same_runs,
                   count(e.race_id) FILTER (WHERE e.ran AND e.finish <= 3) AS same_top3
            FROM target g LEFT JOIN editions e
                 ON e.horse_id = g.horse_id AND e.stakes_no = g.stakes_no AND e.race_date < g.race_date
            WHERE g.stakes_no IS NOT NULL
            GROUP BY g.race_id, g.horse_id
        ),
        previous_edition AS (
            SELECT g.race_id, arg_max(e.race_id, e.race_date) AS prev_edition_id
            FROM (SELECT DISTINCT race_id, race_date, stakes_no FROM target WHERE stakes_no IS NOT NULL) g
            JOIN (SELECT DISTINCT race_id, race_date, stakes_no FROM editions) e
                 ON e.stakes_no = g.stakes_no AND e.race_date < g.race_date
            GROUP BY g.race_id
        )
        SELECT t.race_id, t.horse_id,
               CASE WHEN t.grade_code IN {_GRADED} THEN 1.0 ELSE 0.0 END AS "重賞か",
               {grade_now} AS "格",
               coalesce(t.weight_type, '不明') AS "重量種別",
               t.carried - t.top_carried AS "トップハンデとの差",
               CASE WHEN t.prev IS NULL THEN '前走なし' ELSE {grade_prev} END AS "前走の格",
               coalesce(c.graded_runs, 0) AS "重賞の出走数",
               coalesce(c.graded_top3, 0) AS "重賞の3着以内の数",
               coalesce(c.graded_wins, 0) AS "重賞の勝利数",
               coalesce(c.g1_top3, 0) AS "G1の3着以内の数",
               coalesce(c.step_top3, 0) AS "今回の格以上での3着以内の数",
               c.last_graded_finish AS "直近の重賞の着順",
               s.same_runs AS "同じ重賞の出走数",
               s.same_top3 AS "同じ重賞の3着以内の数",
               pf.finish AS "前年の同じ重賞の着順"
        FROM target t
        LEFT JOIN career c USING (race_id, horse_id)
        LEFT JOIN same_stakes s USING (race_id, horse_id)
        LEFT JOIN previous_edition pe ON pe.race_id = t.race_id
        LEFT JOIN f pf ON pf.race_id = pe.prev_edition_id AND pf.horse_id = t.horse_id AND pf.ran
        """
