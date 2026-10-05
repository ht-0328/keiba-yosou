"""地方（nvdata-store）の取得の状況を読む部品（``LocalStoreReader``）のテスト。実DB は使わず、地方の競馬場コードで作った合成DB で確かめる。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from 共通.db_lock import DatabaseLock
from 合成DB import synth
from 取得と予想の状況.local_store_reader import LocalStoreReader
from 取得と予想の状況.store_screen_probe import LOCAL_STORE_APP, StoreScreenProbe
from 取得と予想の状況.tests.test_store_screen_probe import CLOSED_URL

#: 大井（地方の競馬場コード 44）。
OOI = "44"
#: 合成DB の確定前のレースの日の朝。
RACE_MORNING = datetime(2025, 4, 19, 9, 0, 0)


def local_db(path: Path) -> Path:
    """大井の確定成績1レース（2025-04-12）と、出馬表1レース（2025-04-19）。地方の DB は中央のレースを含まない。"""
    return synth.build_db(path, synth.simple_race("20250412", "01", venue=OOI).extend(synth.card_race("20250419", "01", stage="2", venue=OOI)))


def reader(path: Path, *, lock_timeout: float = 1.0) -> LocalStoreReader:
    return LocalStoreReader(path, StoreScreenProbe(CLOSED_URL, LOCAL_STORE_APP, timeout=0.5), lock_timeout=lock_timeout)


def test_地方の出馬表と確定成績と同期の記録を読む(tmp_path: Path) -> None:
    status = reader(local_db(tmp_path / "nv.duckdb")).read(RACE_MORNING)
    assert status.db_error is None and status.file.exists
    assert (status.results.first_date, status.results.last_date, status.results.races) == ("2025-04-12", "2025-04-12", 1)
    (day,) = status.days
    assert (day.day, day.weekday, day.venues, day.races, day.cards, day.finished, day.with_odds) == ("2025-04-19", "土", ("大井",), 1, 1, 0, 0)
    assert [(record.dataspec, record.title) for record in status.sync_records] == [("RACE", "レース情報（出馬表・成績・払戻・オッズ）")]
    assert not status.store.running and status.store.name == "nvdata-store" and "nvdata-store の run.bat" in status.store.describe()


def test_DBのファイルが無ければ読まない(tmp_path: Path) -> None:
    status = reader(tmp_path / "none.duckdb").read(RACE_MORNING)
    assert not status.file.exists and status.db_error is None and status.results is None and status.days == []


def test_nvdata_storeの取得中なら読めないと言う(tmp_path: Path) -> None:
    path = local_db(tmp_path / "busy.duckdb")
    lock = DatabaseLock(path)
    assert lock.acquire(timeout=1)
    try:
        status = reader(path, lock_timeout=0.2).read(RACE_MORNING)
    finally:
        lock.release()
    assert status.db_error.startswith("DB を別の画面") and status.results is None and status.days == []
