"""過去の傾きの表と、レースごとの傾きをファイルにとっておき、元DB が変わったら作り直す。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from yosou.shared.repository import DbStamp

from .prior_slope_table import PriorSlopeTable
from .prior_slope_table_builder import PriorSlopeTableBuilder
from .race_slopes import RaceSlopes
from .repository import BiasRunRepository, PriorSlopeTableRepository

#: keiba-yosou のリポジトリ直下（src/yosou/track_bias/ から3つ上）と、とっておく場所の既定。
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CACHE_FOLDER = _PROJECT_ROOT / "reports" / "トラックバイアス" / "cache"


def bias_cache_folder_beside(development_root: Path) -> Path:
    """予想「展開から着順を予想」の置き場所（``reports/展開から着順を予想``）の隣の ``トラックバイアス/cache/``（既定の置き場所と同じ決め方。
    テストでは一時フォルダの隣になり、本物の reports/ を書き換えない）。"""
    return Path(development_root).parent / "トラックバイアス" / "cache"


class PriorSlopeTableStore:
    """レースごとの傾き（``RaceSlopes`` の表。2011年からの全レース）と過去の傾きの表を ``folder`` に pickle で書き
    （``PriorSlopeTableRepository``）、元DB（パスと更新時刻。``DbStamp``）が同じなら読んで使い回す。
    元DB に新しい成績が入ると作り直す（``rebuild`` は元DB が同じでも作り直す）。元DB の見分け方は表 G の ``AdvantageTableStore`` と同じ。
    """

    def __init__(self, folder: Path = DEFAULT_CACHE_FOLDER) -> None:
        self._repository = PriorSlopeTableRepository(folder)
        self._stamp = DbStamp()

    def load(self, con: duckdb.DuckDBPyConnection, db_path: Path | None = None) -> tuple[pd.DataFrame, PriorSlopeTable]:
        """（レースごとの傾きの表, 過去の傾きの表）。とっておいたもの（元DB が同じとき）か、作り直したもの。"""
        stamp = self._stamp.of_connection(con, db_path)
        if self._repository.saved_stamp() == stamp:
            return self._repository.read()
        return self._build(con, stamp)

    def rebuild(self, con: duckdb.DuckDBPyConnection, db_path: Path | None = None) -> tuple[pd.DataFrame, PriorSlopeTable]:
        """元DB が同じでも、作り直して書く。"""
        return self._build(con, self._stamp.of_connection(con, db_path))

    def _build(self, con: duckdb.DuckDBPyConnection, stamp: dict[str, object]) -> tuple[pd.DataFrame, PriorSlopeTable]:
        """元DB の全出走からレースごとの傾きと過去の傾きの表を作って書く。"""
        slopes = RaceSlopes().of(BiasRunRepository(con).read())
        table = PriorSlopeTableBuilder().build(slopes)
        self._repository.write(slopes, table, stamp)
        return slopes, table
