"""元DB のファイルの見分け（パスと更新時刻）。"""

from __future__ import annotations

from pathlib import Path

import duckdb


class DbStamp:
    """とっておいた表が「今の元DB から作ったものか」を見分ける印。元DB のファイルのパスと更新時刻の組で、
    表 G（展開スコア）・過去の傾きの表（トラックバイアス）・表 W（馬体重の表）のキャッシュが共通に使う。
    """

    def of(self, db_path: Path) -> dict[str, object]:
        """``db_path`` の元DB の印。ファイルが無ければ更新時刻は None。"""
        path = Path(db_path)
        return {"db": str(path.resolve()), "mtime": path.stat().st_mtime if path.exists() else None}

    def of_connection(self, con: duckdb.DuckDBPyConnection, db_path: Path | None) -> dict[str, object]:
        """``db_path`` を渡されればその元DB の印、省かれれば接続している元DB の印。"""
        return self.of(db_path if db_path is not None else self.db_path_of(con))

    def db_path_of(self, con: duckdb.DuckDBPyConnection) -> Path:
        """接続している元DB のファイル（DuckDB の ``database_list`` の最初のもの）。"""
        rows = con.execute("PRAGMA database_list").fetchall()
        if not rows:
            raise LookupError("接続している元DB のファイルが分かりません")
        return Path(rows[0][2])
