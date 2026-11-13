"""元DB の写しを作る・消す（裏で動かす WIN5 の予想が、ほかのレースの取り込みと予想と元DB を取り合わないように）。"""

from __future__ import annotations

import shutil
from pathlib import Path

from 共通 import db
from 共通.db_lock import DatabaseLock

from 発走前の通知.folders import WIN5_SNAPSHOT_FOLDER

#: 写しのファイル名。
SNAPSHOT_NAME = "jvdata.duckdb"
#: DuckDB の書きかけの記録（あれば一緒に写す）。
_WAL_SUFFIX = ".wal"


class DatabaseSnapshot:
    """``take`` は、取得の画面と同じ規約のロック（``<DB>.ui.lock``）を取ってから、元DB のファイルを ``<folder>/<開催日>/`` に写す
    （8.6GB で 7 秒ほど）。取れなければ ``BlockingIOError``（呼ぶ側が待ってやり直す）。写している間は道具が元DB を開けないが、
    取り込み（jvstore）はこの流れの中で順に動かすので、写しと重ならない。``remove`` は写しをフォルダごと消す（消せなければ次の ``take`` で消す）。"""

    def __init__(self, db_path: str | Path | None = None, folder: Path = WIN5_SNAPSHOT_FOLDER,
                 lock_timeout: float = db.LOCK_TIMEOUT_SECONDS) -> None:
        self._db_path = db_path
        self._folder = Path(folder)
        self._lock_timeout = lock_timeout

    def take(self, day: str) -> Path:
        source = db.resolve_db(self._db_path)
        target = self._folder / day / SNAPSHOT_NAME
        self.remove(day)
        target.parent.mkdir(parents=True, exist_ok=True)
        lock = DatabaseLock(source)
        if not lock.acquire(timeout=self._lock_timeout):
            raise BlockingIOError("DB を別の画面（取得の道具など）で使用中です。WIN5 の予想のための写しを作れませんでした。")
        try:
            shutil.copyfile(source, target)
            wal = Path(str(source) + _WAL_SUFFIX)
            if wal.is_file():
                shutil.copyfile(wal, Path(str(target) + _WAL_SUFFIX))
        finally:
            lock.release()
        return target

    def remove(self, day: str) -> None:
        shutil.rmtree(self._folder / day, ignore_errors=True)
