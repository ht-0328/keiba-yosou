"""同期の記録（``_meta``）を読む。"""

from __future__ import annotations

import duckdb

from 共通 import facts

#: jvdata-store が進捗を書く表と、その列。
_TABLE = "_meta"
_COLUMNS = ("key", "value")


class SyncRecordRepository:
    """``_meta`` の全部の鍵と値を読む。表の無い DB（まだ1度も取り込んでいない）では空。"""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self) -> dict[str, str]:
        table = facts.optional_relation(self._con, _TABLE, _COLUMNS)
        return dict(self._con.execute(f"SELECT key, value FROM {table} ORDER BY key").fetchall())
