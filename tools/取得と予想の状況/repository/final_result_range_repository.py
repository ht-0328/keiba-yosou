"""中央の確定成績の期間とレース数（``ra``）を読む。"""

from __future__ import annotations

import duckdb

from 共通 import facts, keys
from 取得と予想の状況.final_result_range import FinalResultRange

_TABLE = "ra"
_COLUMNS = (*keys.RACE_KEY, "データ区分")


class FinalResultRangeRepository:
    """``ra`` の確定成績（データ区分 5〜7）の最初と最後の開催日と、レース数を読む。``ra`` の無い DB では空の範囲。

    ``jra_only`` が真なら中央のレースだけ（jvdata-store の DB）。地方競馬DATA の DB（nvdata-store）を読むときは偽にする。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, *, jra_only: bool = True) -> None:
        self._con = con
        self._area = keys.jra_only() if jra_only else "TRUE"

    def read(self) -> FinalResultRange:
        table = facts.optional_relation(self._con, _TABLE, _COLUMNS)
        day = keys.race_date_expr()
        first, last, races = self._con.execute(
            f"SELECT min({day}), max({day}), count(DISTINCT {keys.rid_expr()}) FROM {table} WHERE {self._area} AND {keys.final_only()}"
        ).fetchone()
        return FinalResultRange(first, last, int(races or 0))
