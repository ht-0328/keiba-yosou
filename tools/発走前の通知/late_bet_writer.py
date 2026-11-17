"""発走前の予想と同じ接続で、直前の買い目（道具「地方の直前の買い目」）を出してファイルに書く。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from yosou.shared.feature import PredictionTiming

from 地方の直前の買い目.late_bet_file import LateBetFile
from 地方の直前の買い目.late_bets import LateBets
from 地方の直前の買い目.late_model_store import LateModelStore
from 地方の直前の買い目.late_predictor import LatePredictor
from 地方の直前の買い目.late_probabilities import LateProbabilities
from 地方の直前の買い目.repository import OddsSnapshotRepository


class LateBetWriter:
    """材料は、そのレースの時系列オッズ（``odds_db``。元DB とは別の DuckDB）の断面と、学んだときと同じ全頭の予想のモデルの確率
    （``LateProbabilities``。元DB の接続 ``con`` で出す。予想と同じ接続なので、事実表を作り直さない）。
    当日の時点でだけ出す（前日の時点は馬体重が無く、学んだときと材料が違う）。出せないときは失敗にせず、理由つきの「なし」を書く
    （通知の印と推奨買目は、直前の買い目が出せなくても届ける）。"""

    def __init__(self, store: LateModelStore | None = None, probabilities: LateProbabilities | None = None,
                 file: LateBetFile | None = None) -> None:
        self._store = store or LateModelStore()
        self._probabilities = probabilities or LateProbabilities()
        self._file = file or LateBetFile()

    def write(self, con: duckdb.DuckDBPyConnection, rid: str, out: Path, odds_db: Path | None, db_path: Path | None,
              timing: PredictionTiming) -> LateBets:
        self._file.clear(out)
        try:
            bets = self._bets(con, rid, odds_db, db_path, timing)
        except Exception as error:  # noqa: BLE001 — 直前の買い目が出せなくても、予想（印と推奨買目）は通知する
            bets = LateBets.none(f"{type(error).__name__}: {error}")
        self._file.write(out, bets)
        return bets

    def _bets(self, con: duckdb.DuckDBPyConnection, rid: str, odds_db: Path | None, db_path: Path | None,
              timing: PredictionTiming) -> LateBets:
        if timing is not PredictionTiming.RACE_DAY:
            return LateBets.none("馬体重が届く前の前日の時点では出さない")
        snapshot = self._snapshot(rid, odds_db)
        if snapshot.empty:
            return LateBets.none("時系列オッズの断面がまだ無い")
        predictor = LatePredictor(self._store.load())
        return predictor.bets(rid, snapshot, self._probabilities.of(con, rid, db_path))

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
