"""表 G をファイルにとっておき、元DB が変わったら作り直す。"""

from __future__ import annotations

from pathlib import Path

import duckdb

from yosou.shared.repository import DbStamp

from .advantage_runs import AdvantageRuns
from .advantage_table import AdvantageTable
from .advantage_table_builder import AdvantageTableBuilder
from .repository import AdvantageTableRepository, DevelopmentRunRepository

#: keiba-yosou のリポジトリ直下（src/yosou/development_score/ から3つ上）と、とっておく場所の既定。
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CACHE_FOLDER = _PROJECT_ROOT / "reports" / "展開スコア" / "cache"


def cache_folder_beside(development_root: Path) -> Path:
    """予想「展開から着順を予想」の置き場所（``reports/展開から着順を予想``）の隣の ``展開スコア/cache/``（既定の置き場所と同じ決め方）。

    全頭の予想が S を足すとき、展開の予想の置き場所から表 G の置き場所を決める（テストでは一時フォルダの隣になり、本物の reports/ を書き換えない）。
    """
    return Path(development_root).parent / "展開スコア" / "cache"


class AdvantageTableStore:
    """表 G を ``folder`` に pickle で書き（``AdvantageTableRepository``）、元DB（パスと更新時刻。``DbStamp``）が同じなら読んで使い回す。

    表 G は 2011年からの全出走から作るので、毎回作ると1分ほどかかる。元DB に新しい確定成績が入る（ファイルが更新される）と
    作り直す。``rebuild`` は元DB が同じでも作り直す。作った条件は ``stamp.json`` に書く。
    """

    def __init__(self, folder: Path = DEFAULT_CACHE_FOLDER) -> None:
        self._repository = AdvantageTableRepository(folder)
        self._stamp = DbStamp()

    def load(self, con: duckdb.DuckDBPyConnection, db_path: Path | None = None) -> AdvantageTable:
        """とっておいた表 G（元DB が同じとき）か、作り直した表 G。``db_path`` を省くと、接続している元DB のファイル。"""
        stamp = self._stamp.of_connection(con, db_path)
        if self._repository.saved_stamp() == stamp:
            return self._repository.read()
        return self._build(con, stamp)

    def rebuild(self, con: duckdb.DuckDBPyConnection, db_path: Path | None = None) -> AdvantageTable:
        """元DB が同じでも、表 G を作り直して書く。"""
        return self._build(con, self._stamp.of_connection(con, db_path))

    def is_fresh(self, db_path: Path) -> bool:
        """とっておいた表 G が、今の元DB から作ったものか。"""
        return self._repository.saved_stamp() == self._stamp.of(db_path)

    def _build(self, con: duckdb.DuckDBPyConnection, stamp: dict[str, object]) -> AdvantageTable:
        """元DB の全出走から表 G を作って書く。"""
        table = AdvantageTableBuilder().build(AdvantageRuns().build(DevelopmentRunRepository(con).read()))
        self._repository.write(table, stamp)
        return table
