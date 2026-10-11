"""表 G をファイルにとっておき、元DB が変わったら作り直す。"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd

from .advantage_runs import AdvantageRuns
from .advantage_table import AdvantageTable
from .advantage_table_builder import AdvantageTableBuilder
from .development_run_repository import DevelopmentRunRepository

#: keiba-yosou のリポジトリ直下（src/yosou/development_score/ から3つ上）と、とっておく場所の既定。
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CACHE_FOLDER = _PROJECT_ROOT / "reports" / "展開スコア" / "cache"
_TABLE_FILE, _STAMP_FILE = "表G.pkl", "stamp.json"


def cache_folder_beside(development_root: Path) -> Path:
    """予想「展開から着順を予想」の置き場所（``reports/展開から着順を予想``）の隣の ``展開スコア/cache/``（既定の置き場所と同じ決め方）。

    全頭の予想が S を足すとき、展開の予想の置き場所から表 G の置き場所を決める（テストでは一時フォルダの隣になり、本物の reports/ を書き換えない）。
    """
    return Path(development_root).parent / "展開スコア" / "cache"


class AdvantageTableStore:
    """表 G を ``folder`` に pickle で書き、元DB（パスと更新時刻）が同じなら読んで使い回す。

    表 G は 2011年からの全出走から作るので、毎回作ると1分ほどかかる。元DB に新しい確定成績が入る（ファイルが更新される）と
    作り直す。``rebuild`` で強制的に作り直す。作った条件は ``stamp.json`` に書く。
    """

    def __init__(self, folder: Path = DEFAULT_CACHE_FOLDER) -> None:
        self._folder = Path(folder)

    def load(self, con: duckdb.DuckDBPyConnection, db_path: Path | None = None, rebuild: bool = False) -> AdvantageTable:
        """とっておいた表 G（元DB が同じとき）か、作り直した表 G。``db_path`` を省くと、接続している元DB のファイル。"""
        stamp = self._stamp_of(db_path if db_path is not None else self.db_path_of(con))
        if not rebuild and self._saved_stamp() == stamp:
            return self._read()
        table = AdvantageTableBuilder().build(AdvantageRuns().build(DevelopmentRunRepository(con).read()))
        self._write(table, stamp)
        return table

    @staticmethod
    def db_path_of(con: duckdb.DuckDBPyConnection) -> Path:
        """接続している元DB のファイル（DuckDB の ``database_list`` の最初のもの）。"""
        rows = con.execute("PRAGMA database_list").fetchall()
        if not rows:
            raise LookupError("接続している元DB のファイルが分かりません")
        return Path(rows[0][2])

    def is_fresh(self, db_path: Path) -> bool:
        """とっておいた表 G が、今の元DB から作ったものか。"""
        return self._saved_stamp() == self._stamp_of(db_path)

    def _stamp_of(self, db_path: Path) -> dict[str, object]:
        path = Path(db_path)
        return {"db": str(path.resolve()), "mtime": path.stat().st_mtime if path.exists() else None}

    def _saved_stamp(self) -> dict[str, object] | None:
        path = self._folder / _STAMP_FILE
        if not path.exists() or not (self._folder / _TABLE_FILE).exists():
            return None
        saved = json.loads(path.read_text(encoding="utf-8"))
        return {"db": saved.get("db"), "mtime": saved.get("mtime")}

    def _read(self) -> AdvantageTable:
        saved = pd.read_pickle(self._folder / _TABLE_FILE)
        return AdvantageTable(saved["frame"], saved["pool"], saved["as_of"])

    def _write(self, table: AdvantageTable, stamp: dict[str, object]) -> None:
        self._folder.mkdir(parents=True, exist_ok=True)
        pd.to_pickle({"frame": table.frame, "pool": table.pool, "as_of": table.as_of}, self._folder / _TABLE_FILE)
        as_of = None if table.as_of is None else f"{table.as_of:%Y-%m-%d}"
        (self._folder / _STAMP_FILE).write_text(json.dumps({**stamp, "as_of": as_of}, ensure_ascii=False, indent=2), encoding="utf-8")
