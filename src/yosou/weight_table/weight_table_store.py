"""表 W をファイルにとっておき、元DB が変わったら作り直す。"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd

from yosou.development_score import AdvantageTableStore

from .weight_run_repository import WeightRunRepository
from .weight_runs import WeightRuns
from .weight_table import WeightTable
from .weight_table_builder import WeightTableBuilder

#: keiba-yosou のリポジトリ直下（src/yosou/weight_table/ から3つ上）と、とっておく場所の既定。
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CACHE_FOLDER = _PROJECT_ROOT / "reports" / "馬体重の表" / "cache"
_TABLE_FILE, _STAMP_FILE = "表W.pkl", "stamp.json"


def weight_cache_folder_beside(development_root: Path) -> Path:
    """予想「展開から着順を予想」の置き場所（``reports/展開から着順を予想``）の隣の ``馬体重の表/cache/``（既定の置き場所と同じ決め方。
    テストでは一時フォルダの隣になり、本物の reports/ を書き換えない）。"""
    return Path(development_root).parent / "馬体重の表" / "cache"


class WeightTableStore:
    """表 W を ``folder`` に pickle で書き、元DB（パスと更新時刻）が同じなら読んで使い回す。元DB に新しい成績が入ると作り直す
    （``rebuild`` で強制）。元DB の見分け方は表 G の ``AdvantageTableStore`` と同じ。"""

    def __init__(self, folder: Path = DEFAULT_CACHE_FOLDER) -> None:
        self._folder = Path(folder)

    def load(self, con: duckdb.DuckDBPyConnection, db_path: Path | None = None, rebuild: bool = False) -> WeightTable:
        stamp = self._stamp_of(db_path if db_path is not None else AdvantageTableStore.db_path_of(con))
        if not rebuild and self._saved_stamp() == stamp:
            return self._read()
        table = WeightTableBuilder().build(WeightRuns().build(WeightRunRepository(con).read()))
        self._write(table, stamp)
        return table

    def _stamp_of(self, db_path: Path) -> dict[str, object]:
        path = Path(db_path)
        return {"db": str(path.resolve()), "mtime": path.stat().st_mtime if path.exists() else None}

    def _saved_stamp(self) -> dict[str, object] | None:
        path = self._folder / _STAMP_FILE
        if not path.exists() or not (self._folder / _TABLE_FILE).exists():
            return None
        saved = json.loads(path.read_text(encoding="utf-8"))
        return {"db": saved.get("db"), "mtime": saved.get("mtime")}

    def _read(self) -> WeightTable:
        saved = pd.read_pickle(self._folder / _TABLE_FILE)
        return WeightTable(saved["frame"], saved["as_of"])

    def _write(self, table: WeightTable, stamp: dict[str, object]) -> None:
        self._folder.mkdir(parents=True, exist_ok=True)
        pd.to_pickle({"frame": table.frame, "as_of": table.as_of}, self._folder / _TABLE_FILE)
        as_of = None if table.as_of is None else f"{table.as_of:%Y-%m-%d}"
        (self._folder / _STAMP_FILE).write_text(json.dumps({**stamp, "as_of": as_of}, ensure_ascii=False, indent=2), encoding="utf-8")
