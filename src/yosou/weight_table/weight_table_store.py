"""表 W をファイルにとっておき、元DB が変わったら作り直す。"""

from __future__ import annotations

from pathlib import Path

import duckdb

from yosou.shared.repository import DbStamp

from .repository import WeightRunRepository, WeightTableRepository
from .weight_runs import WeightRuns
from .weight_table import WeightTable
from .weight_table_builder import WeightTableBuilder

#: keiba-yosou のリポジトリ直下（src/yosou/weight_table/ から3つ上）と、とっておく場所の既定。
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CACHE_FOLDER = _PROJECT_ROOT / "reports" / "馬体重の表" / "cache"


def weight_cache_folder_beside(development_root: Path) -> Path:
    """予想「展開から着順を予想」の置き場所（``reports/展開から着順を予想``）の隣の ``馬体重の表/cache/``（既定の置き場所と同じ決め方。
    テストでは一時フォルダの隣になり、本物の reports/ を書き換えない）。"""
    return Path(development_root).parent / "馬体重の表" / "cache"


class WeightTableStore:
    """表 W を ``folder`` に pickle で書き（``WeightTableRepository``）、元DB（パスと更新時刻。``DbStamp``）が同じなら読んで使い回す。
    元DB に新しい成績が入ると作り直す（``rebuild`` は元DB が同じでも作り直す）。元DB の見分け方は表 G の ``AdvantageTableStore`` と同じ。"""

    def __init__(self, folder: Path = DEFAULT_CACHE_FOLDER) -> None:
        self._repository = WeightTableRepository(folder)
        self._stamp = DbStamp()

    def load(self, con: duckdb.DuckDBPyConnection, db_path: Path | None = None) -> WeightTable:
        """とっておいた表 W（元DB が同じとき）か、作り直した表 W。``db_path`` を省くと、接続している元DB のファイル。"""
        stamp = self._stamp.of_connection(con, db_path)
        if self._repository.saved_stamp() == stamp:
            return self._repository.read()
        return self._build(con, stamp)

    def rebuild(self, con: duckdb.DuckDBPyConnection, db_path: Path | None = None) -> WeightTable:
        """元DB が同じでも、表 W を作り直して書く。"""
        return self._build(con, self._stamp.of_connection(con, db_path))

    def _build(self, con: duckdb.DuckDBPyConnection, stamp: dict[str, object]) -> WeightTable:
        """元DB の全出走から表 W を作って書く。"""
        table = WeightTableBuilder().build(WeightRuns().build(WeightRunRepository(con).read()))
        self._repository.write(table, stamp)
        return table
