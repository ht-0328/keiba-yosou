"""まとまり D（その日の馬場の傾向）を、元DB の事実表から読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from 共通 import facts

#: 2011〜2014年の3着以内の馬の平均（4コーナーの位置を頭数で割った値・馬番が頭数の半分以下の割合）。合い具合の基準にする。
_TYPICAL_FRONT = {"芝": 0.361, "ダート": 0.298}
_TYPICAL_INNER = {"芝": 0.504, "ダート": 0.479}
#: 何レース前までの結果を使うか（2 なら、2つ前のレースまで）。
_GAP = 2


class DayBiasReader:
    """対象（中央の平地の出走。``first_day`` 以降）ごとに、D の5つを1本の SQL で読む（1行 = 1頭の出走）。

    - 前残りの度合い: 先のレースの3着以内の馬の、4コーナーの位置（頭数で割った 0〜1。小さいほど前）の平均
    - 内の度合い: 先のレースの3着以内の馬のうち、馬番が頭数の半分以下の割合
    - 脚質と馬場の合い具合: （前残りの度合い − 基準）×（その馬の直近3走の4コーナーの位置の平均 − 0.5）。前が残る日の先行馬で大きい
    - 枠と馬場の合い具合: （内の度合い − 基準）×（0.5 − 馬番 ÷ 頭数）。内が来る日の内の馬で大きい
    先のレースが無いときは、数だけ 0 で、ほかは欠損値。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, first_day: date) -> pd.DataFrame:
        facts.ensure_facts(self._con)
        frame = self._con.execute(self._sql(), [first_day.isoformat()]).df()
        return frame.assign(race_id=frame["race_id"].astype(str), horse_id=frame["horse_id"].astype(str))

    @staticmethod
    def _sql() -> str:
        front = " ".join(f"WHEN '{surface}' THEN {value}" for surface, value in _TYPICAL_FRONT.items())
        inner = " ".join(f"WHEN '{surface}' THEN {value}" for surface, value in _TYPICAL_INNER.items())
        return f"""
        WITH f AS (
            SELECT race_id, race_date, venue, surface, race_no, horse_id, horse_no, field_size, finish, ran,
                   CASE WHEN ran THEN corner4::DOUBLE / field_size END AS pos4,
                   CASE WHEN horse_no <= field_size / 2.0 THEN 1.0 ELSE 0.0 END AS inner_half
            FROM {facts.FACTS_TABLE}
        ),
        styled AS (
            SELECT f.*, avg(pos4) OVER (PARTITION BY horse_id ORDER BY race_date, race_id ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING) AS style_pos
            FROM f
        ),
        races AS (
            SELECT DISTINCT race_id, race_date, venue, surface, race_no FROM f WHERE race_date >= ? AND surface <> '障害'
        ),
        day AS (
            SELECT r.race_id, count(DISTINCT e.race_id) AS earlier, avg(e.pos4) AS front, avg(e.inner_half) AS inner_share
            FROM races r JOIN f e ON e.race_date = r.race_date AND e.venue = r.venue AND e.surface = r.surface
                                 AND e.race_no <= r.race_no - {_GAP} AND e.ran AND e.finish <= 3
            GROUP BY r.race_id
        )
        SELECT s.race_id, s.horse_id,
               CAST(coalesce(d.earlier, 0) AS DOUBLE) AS "その日の先のレースの数",
               d.front AS "その日の前残りの度合い",
               d.inner_share AS "その日の内の度合い",
               (d.front - CASE r.surface {front} END) * (s.style_pos - 0.5) AS "脚質と馬場の合い具合",
               (d.inner_share - CASE r.surface {inner} END) * (0.5 - s.horse_no::DOUBLE / s.field_size) AS "枠と馬場の合い具合"
        FROM styled s JOIN races r USING (race_id) LEFT JOIN day d USING (race_id)
        """
