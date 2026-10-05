"""地方競馬DATA の DB（nvdata-store）と、その取得の画面から、地方の取得の状況を集める。"""

from __future__ import annotations

from datetime import datetime
from itertools import groupby
from pathlib import Path

import duckdb

from 共通 import db
from 共通.race_signals import RaceScope, RaceSignalReader
from 取得と予想の状況.acquisition_day import AcquisitionDay
from 取得と予想の状況.local_store_status import LocalStoreStatus
from 取得と予想の状況.repository import FinalResultRangeRepository, SyncRecordRepository
from 取得と予想の状況.store_file import StoreFile
from 取得と予想の状況.store_screen import StoreScreen
from 取得と予想の状況.store_screen_probe import LOCAL_STORE_APP, LOCAL_STORE_URL, StoreScreenProbe
from 取得と予想の状況.sync_record import LOCAL_DATASPEC_TITLES, SyncRecord

#: 地方競馬DATA の DB の既定の場所。jvdata-store の隣に nvdata-store を置いている前提。
DEFAULT_LOCAL_DB = db.DEFAULT_DB.parents[1] / "nvdata-store" / "nvdata.duckdb"
#: DB のロックを待つ上限（秒）。nvdata-store の取得中なら待たずに「読めない」と出す（画面は30秒ごとに読み直す）。
DEFAULT_LOCK_TIMEOUT_SECONDS = 1.0


class LocalStoreReader:
    """nvdata-store の DB を短く開いて、確定成績の期間・同期の記録・今日以降の開催日ごとの材料の数を読む。SQL は持たない。

    DB は読むだけで、nvdata-store の画面と同じ規約のロック（``<DB>.ui.lock``）を取ってから開き、読み終えたらすぐ手放す。
    予想は地方を対象にしていないので、予想の判定は出さない。
    """

    def __init__(self, db_path: Path = DEFAULT_LOCAL_DB, probe: StoreScreenProbe | None = None,
                 lock_timeout: float = DEFAULT_LOCK_TIMEOUT_SECONDS) -> None:
        self._db_path = Path(db_path)
        self._probe = probe or StoreScreenProbe(LOCAL_STORE_URL, LOCAL_STORE_APP)
        self._lock_timeout = lock_timeout

    def read(self, now: datetime) -> LocalStoreStatus:
        store, file = self._probe.probe(), StoreFile.read(self._db_path)
        if not file.exists:
            return LocalStoreStatus(store, file, None, None)
        try:
            return self._open_and_read(store, file, now)
        except BlockingIOError as error:
            return LocalStoreStatus(store, file, str(error), None)

    def _open_and_read(self, store: StoreScreen, file: StoreFile, now: datetime) -> LocalStoreStatus:
        """DB を短く開いて読む。nvdata-store の取得中で開けなければ ``BlockingIOError``。"""
        with db.open_db(self._db_path, lock_timeout=self._lock_timeout) as con:
            return self._with_db(con, store, file, now)

    @staticmethod
    def _with_db(con: duckdb.DuckDBPyConnection, store: StoreScreen, file: StoreFile, now: datetime) -> LocalStoreStatus:
        signals = RaceSignalReader(con).read(RaceScope.days(now.date().isoformat(), jra_only=False))
        days = [AcquisitionDay.summarize(day, list(group)) for day, group in groupby(signals, key=lambda each: each.race_date)]
        return LocalStoreStatus(
            store=store, file=file, db_error=None, results=FinalResultRangeRepository(con, jra_only=False).read(),
            sync_records=SyncRecord.from_meta(SyncRecordRepository(con).read(), LOCAL_DATASPEC_TITLES), days=days,
        )
