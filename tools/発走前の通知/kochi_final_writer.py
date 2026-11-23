"""発走前の予想と同じ接続で、高知ファイナルの買い目（道具「高知ファイナルの買い目」）を出してファイルに書く。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from 共通 import facts

from 地方の直前の買い目.repository import OddsSnapshotRepository

from 高知ファイナルの買い目.final_bet_file import FinalBetFile
from 高知ファイナルの買い目.final_bets import FinalBets
from 高知ファイナルの買い目.final_model_store import FinalModelStore
from 高知ファイナルの買い目.final_predictor import FinalPredictor
from 高知ファイナルの買い目.repository import FinalRaceRepository, KochiRunRepository

#: 予想するレースの出走馬に事実表と同じ列を付けた一時表の名前。
ENTRY_TABLE = "kochi_final_entries"


class KochiFinalWriter:
    """高知のその日の最終レース「ファイナルレース」のときだけ書く（ほかのレースはファイルを作らず、通知にも出ない）。
    材料は、同じ接続の事実表（予想が作ったものを使い回す）＋そのレースの出走馬（``facts.build_entry_facts``）と、時系列オッズの断面
    （``odds_db``。元DB とは別の DuckDB）。出せないときは失敗にせず、理由つきの「なし」を書く（通知の印とほかの買い目は届ける）。"""

    def __init__(self, store: FinalModelStore | None = None, file: FinalBetFile | None = None) -> None:
        self._store = store or FinalModelStore()
        self._file = file or FinalBetFile()

    def write(self, con: duckdb.DuckDBPyConnection, rid: str, out: Path, odds_db: Path | None) -> FinalBets | None:
        self._file.clear(out)
        if not FinalRaceRepository(con).is_final(rid):
            return None
        try:
            bets = self._bets(con, rid, odds_db)
        except Exception as error:  # noqa: BLE001 — 高知ファイナルの買い目が出せなくても、予想（印と印の買い目）は通知する
            bets = FinalBets.none(f"{type(error).__name__}: {error}")
        self._file.write(out, bets)
        return bets

    def _bets(self, con: duckdb.DuckDBPyConnection, rid: str, odds_db: Path | None) -> FinalBets:
        snapshot = self._snapshot(rid, odds_db)
        if snapshot.empty:
            return FinalBets.none("時系列オッズの断面がまだ無い")
        predictor = FinalPredictor(self._store.load(), self._store.popularity_rates())
        facts.ensure_facts(con)
        facts.build_entry_facts(con, facts.EntryScope(rid), name=ENTRY_TABLE)
        return predictor.bets(rid, KochiRunRepository(con).read(ENTRY_TABLE), snapshot)

    @staticmethod
    def _snapshot(rid: str, odds_db: Path | None) -> pd.DataFrame:
        """時系列オッズの断面。ファイルがまだ無ければ（取り込めなかった）空の表。"""
        if odds_db is None or not Path(odds_db).is_file():
            return pd.DataFrame()
        history = duckdb.connect(str(odds_db), read_only=True)
        try:
            return OddsSnapshotRepository(history).load(rid)
        finally:
            history.close()
