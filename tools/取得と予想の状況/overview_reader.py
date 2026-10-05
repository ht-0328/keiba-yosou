"""取得と予想の状況を、中央と地方の DB・予想の結果・取得の画面・モデルの置き場所から集めて ``Overview`` にする。"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import replace
from datetime import datetime
from itertools import groupby
from pathlib import Path

import duckdb

from 共通 import db
from 共通.filters import parse_date
from 共通.race_signals import RaceSignalReader, RaceSignals
from 取得と予想の状況.day_status import DayStatus
from 取得と予想の状況.forecast_check import ForecastCheck
from 取得と予想の状況.local_store_reader import LocalStoreReader
from 取得と予想の状況.local_store_status import LocalStoreStatus
from 取得と予想の状況.model_file_scanner import ModelFileScanner
from 取得と予想の状況.overview import Overview
from 取得と予想の状況.race_status import RaceStatus
from 取得と予想の状況.repository import FinalResultRangeRepository, SyncRecordRepository
from 取得と予想の状況.store_file import StoreFile
from 取得と予想の状況.store_screen_probe import StoreScreenProbe
from 取得と予想の状況.sync_record import JRA_DATASPEC_TITLES, SyncRecord
from 今週の予想.forecast_store import ForecastStore
from 今週の予想.model_folders import MODEL_ROOTS

#: DB を開く関数の型。入ると接続、抜けると閉じる（``db.open_db`` や画面のセッションの ``peek``）。
Connect = Callable[[], AbstractContextManager[duckdb.DuckDBPyConnection]]


class OverviewReader:
    """``connect`` で中央の DB を短く開き、今日以降のレースの材料の有無と予想の判定を集める。地方は ``local`` に任せる。SQL は持たない。

    中央の DB が取得中で開けない（``BlockingIOError``）ときも、jvdata-store の画面・DB のファイル・モデルの置き場所・地方は見て返す。
    ``now`` はテストで差し替える。``local`` は地方（nvdata-store）を読む部品（None なら地方を見ない）。
    """

    def __init__(self, *, connect: Connect, db_path: Path, forecasts: ForecastStore, now: Callable[[], datetime] = datetime.now,
                 probe: StoreScreenProbe | None = None, scanner: ModelFileScanner | None = None,
                 local: LocalStoreReader | None = None) -> None:
        self._connect = connect
        self._db_path = Path(db_path)
        self._forecasts = forecasts
        self._now = now
        self._probe = probe or StoreScreenProbe()
        self._scanner = scanner or ModelFileScanner(MODEL_ROOTS)
        self._local = local

    def read(self, day: str | None = None) -> Overview:
        """``day``（``YYYY-MM-DD``）を渡すと、その日のレースごとの表にする。省くと今日（今日にレースが無ければ次の開催日）。"""
        now = self._now()
        wanted = parse_date(day) if day else None
        try:
            overview = self._open_and_read(now, wanted)
        except BlockingIOError as error:
            overview = self._without_db(now, wanted, str(error))
        # 地方は、中央の DB を閉じてから読む（2つの DB のロックを同時に持たない）
        return replace(overview, local=self._read_local(now))

    def _open_and_read(self, now: datetime, wanted: str | None) -> Overview:
        """DB を短く開いて読む。取得中で開けなければ ``BlockingIOError``。"""
        with self._connect() as con:
            return self._with_db(con, now, wanted)

    def _with_db(self, con: duckdb.DuckDBPyConnection, now: datetime, wanted: str | None) -> Overview:
        reader = RaceSignalReader(con)
        check = ForecastCheck(self._forecasts)
        upcoming = self._statuses(reader.read_days(now.date().isoformat()), check)
        day = wanted or self._default_day(upcoming, now)
        races = self._races_of(day, upcoming, reader, check)
        return Overview(
            now=now, store=self._probe.probe(), db_file=StoreFile.read(self._db_path), db_error=None,
            results=FinalResultRangeRepository(con).read(),
            sync_records=SyncRecord.from_meta(SyncRecordRepository(con).read(), JRA_DATASPEC_TITLES),
            days=self._days(upcoming), day=day, races=races, next_race=self._next_race(day, races, now),
            models=self._scanner.scan(), missing_model_roots=self._scanner.missing_roots(),
        )

    def _without_db(self, now: datetime, wanted: str | None, error: str) -> Overview:
        return Overview(now=now, store=self._probe.probe(), db_file=StoreFile.read(self._db_path), db_error=error, results=None,
                        day=wanted, models=self._scanner.scan(), missing_model_roots=self._scanner.missing_roots())

    def _read_local(self, now: datetime) -> LocalStoreStatus | None:
        """地方の取得の状況。地方を見ないなら None。"""
        return self._local.read(now) if self._local is not None else None

    @staticmethod
    def _statuses(signals: list[RaceSignals], check: ForecastCheck) -> list[RaceStatus]:
        return [RaceStatus(each, check.check(each)) for each in signals]

    @staticmethod
    def _default_day(upcoming: list[RaceStatus], now: datetime) -> str | None:
        """今日にレースがあれば今日、無ければ次の開催日。今日以降にレースが無ければ None。"""
        today = now.date().isoformat()
        if any(status.signals.race_date == today for status in upcoming):
            return today
        return upcoming[0].signals.race_date if upcoming else None

    @staticmethod
    def _races_of(day: str | None, upcoming: list[RaceStatus], reader: RaceSignalReader, check: ForecastCheck) -> list[RaceStatus]:
        """その日のレース。今日以降の並びにあればそこから、無ければ（過去の日）DB から読む。"""
        if day is None:
            return []
        if any(status.signals.race_date == day for status in upcoming):
            return [status for status in upcoming if status.signals.race_date == day]
        return OverviewReader._statuses(reader.read_days(day, day), check)

    @staticmethod
    def _days(upcoming: list[RaceStatus]) -> list[DayStatus]:
        """開催日ごとに数える（並びは開催日の順になっている）。"""
        return [DayStatus.summarize(day, list(statuses)) for day, statuses in groupby(upcoming, key=lambda status: status.signals.race_date)]

    @staticmethod
    def _next_race(day: str | None, races: list[RaceStatus], now: datetime) -> RaceStatus | None:
        """今日の、これから発走するいちばん早いレース。今日を見ていなければ None。"""
        if day != now.date().isoformat():
            return None
        coming = [status for status in races if (status.signals.post_datetime() or now) > now]
        return min(coming, key=lambda status: status.signals.post_datetime(), default=None)
