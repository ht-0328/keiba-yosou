"""期間の、特別登録のある平地のレースの一覧を読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from 共通 import codes, keys, registration

#: 平地でないレース（障害は予測しない）。
_JUMP = "障害"


class RegistrationListRepository:
    """期間の特別登録のある平地のレース（rid・開催日・競走名・グレード・登録頭数）を読む（1 SQL）。

    ``predict --all`` と ``registrations`` が使う（設計書 04 の repository/）。同じレースに複数の版があれば、月曜の版（データ区分 2）を
    優先し、同じ版なら作成日の新しいもの。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, begin: date, end: date | None = None) -> pd.DataFrame:
        """開催日が ``begin`` 以上 ``end`` 以下（None なら DB にある最後の日まで）のレース。開催日・rid の順。

        列は ``race_id``・``race_date``（日付型）・``race_name``・``grade_code``・``entries``（登録頭数）。
        """
        day = keys.race_date_expr()
        until = "" if end is None else f"AND {day} <= '{end.isoformat()}'"
        sql = f"""
        SELECT {keys.rid_expr()} AS race_id, CAST({day} AS DATE) AS race_date,
               trim({keys.q('競走名本題')}) AS race_name, trim({keys.q('グレードコード')}) AS grade_code,
               TRY_CAST({keys.q('登録頭数')} AS INTEGER) AS entries
        FROM {registration.table_relation(self._con)}
        WHERE {keys.q('データ区分')} IN {keys.sql_list(registration.STAGES)} AND {keys.jra_only()}
          AND {day} >= '{begin.isoformat()}' {until}
          AND {codes.surface_sql(keys.q('トラックコード'))} <> '{_JUMP}'
        {keys.latest_qualify(keys.RACE_KEY)}
        ORDER BY race_date, race_id
        """
        frame = self._con.execute(sql).df()
        return frame.assign(race_date=pd.to_datetime(frame["race_date"]))
