"""開催日・競馬場・レース番号から、特別登録のレースの rid を引く。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import codes, keys, registration


class RegistrationRaceRepository:
    """特別登録（``tk``）から、そのレースの rid を引く（1 SQL）。

    出走馬名表が出る前のレースは ``ra`` にまだ無いので、``race.resolve_rid()`` の代わりに使う（設計書 04 の repository/）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def resolve(self, day: str, venue: str, race_no: int | str) -> str:
        """``day`` は開催日（YYYY-MM-DD）、``venue`` は競馬場の名前かコード。無ければ ``LookupError``。"""
        race_day = pd.Timestamp(day)
        code = codes.venue_code(venue)
        sql = f"""
        SELECT DISTINCT {keys.rid_expr()} FROM {registration.table_relation(self._con)}
        WHERE {keys.q('開催年')} = ? AND {keys.q('開催月日')} = ? AND {keys.q('競馬場コード')} = ? AND {keys.q('レース番号')} = ?
          AND {keys.q('データ区分')} IN {keys.sql_list(registration.STAGES)}
        """
        params = [race_day.strftime("%Y"), race_day.strftime("%m%d"), code, f"{int(race_no):02d}"]
        rows = self._con.execute(sql, params).fetchall()
        if not rows:
            raise LookupError(f"特別登録のレースが見つかりません: {race_day.date()} {codes.venue_name(code)} {int(race_no)}R")
        return rows[0][0]
