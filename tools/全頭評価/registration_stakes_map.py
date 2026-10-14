"""重賞の対応表に、登録の時点のレースを足す。"""

from __future__ import annotations

import duckdb

from 共通 import keys, registration, stakes


class RegistrationStakesMap:
    """重賞の対応表（``stakes_map``。rid → 特別競走番号・グレード・競走名）を用意し、登録の時点のレース（``ra`` にまだ無い）を特別登録から足す（1 SQL）。

    重賞（G1〜G3）でないレースは足さない。``stakes_no_of`` は、そのレースの特別競走番号（重賞でなければ None）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def ensure(self, race_id: str) -> str | None:
        """対応表を用意して登録のレースを足し、そのレースの特別競走番号を返す（重賞でなければ None）。"""
        table = keys.q(stakes.ensure_stakes_map(self._con))
        grades = keys.sql_list(stakes.GRADE_NAMES)
        self._con.execute(f"""
        INSERT INTO {table}
        SELECT {keys.rid_expr()} AS race_id, {keys.q('特別競走番号')} AS stakes_no, trim({keys.q('グレードコード')}) AS grade,
               trim({keys.q('競走名本題')}) AS stakes_name, {keys.race_date_expr()} AS race_date
        FROM {registration.chosen_registration_sql(self._con, race_id)}
        WHERE trim({keys.q('グレードコード')}) IN {grades}
          AND {keys.rid_expr()} NOT IN (SELECT race_id FROM {table})
        """)
        rows = self._con.execute(f"SELECT stakes_no FROM {table} WHERE race_id = ?", [race_id]).fetchall()
        return rows[0][0] if rows else None
