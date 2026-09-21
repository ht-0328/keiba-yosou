"""画面のための DB セッション: 接続と事実表を持ち続け、使っている間だけロックを押さえ、放置したら手放す。

CLI は1回の実行で開いて閉じるが、画面は何度も問い合わせるので、事実表（作るのに数秒）を作り直さない。
ただし jvdata-store の取得（書き込み）を永久に塞がないよう、``idle_seconds`` 放置したら接続を閉じてロックを手放す。
DuckDB の接続は複数スレッドから同時に使えないので、``use()`` を直列にする。
"""

from __future__ import annotations

import contextlib
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import duckdb

from 共通 import db
from 共通.db_lock import DatabaseLock
from 共通.facts import FACTS_TABLE, ensure_facts

#: 放置してから接続を閉じるまでの秒数。
DEFAULT_IDLE_SECONDS = 60.0
#: ロックを待つ上限（秒）。
DEFAULT_LOCK_TIMEOUT = 15.0
#: 使用中の判定の余裕（秒）。
_IDLE_MARGIN = 0.5


class DbSession:
    """1つの DB への、画面用の接続。"""

    def __init__(self, path: Path, *, idle_seconds: float = DEFAULT_IDLE_SECONDS,
                 lock_timeout: float = DEFAULT_LOCK_TIMEOUT) -> None:
        self.path = path
        self.idle_seconds = idle_seconds
        self.lock_timeout = lock_timeout
        self._serial = threading.RLock()
        self._db_lock = DatabaseLock(path)
        self._con: duckdb.DuckDBPyConnection | None = None
        self._timer: threading.Timer | None = None
        self._last_used = 0.0
        self._facts_rows: int | None = None
        self._built_in_s: float | None = None

    @contextlib.contextmanager
    def use(self) -> Iterator[duckdb.DuckDBPyConnection]:
        """接続を借りる。無ければ開き（ロック → 接続 → 事実表）、使い終わったら放置の時計を動かす。"""
        with self._serial:
            self._cancel_timer()
            if self._con is None:
                self._open()
            try:
                yield self._con  # type: ignore[misc]
            finally:
                self._last_used = time.monotonic()
                self._schedule_release()

    def _open(self) -> None:
        if not self._db_lock.acquire(timeout=self.lock_timeout):
            raise BlockingIOError("DB を別の画面（jvdata-store の取得など）で使用中です。終わってから読み込み直してください。")
        try:
            con = db.connect(self.path)
            started = time.perf_counter()
            ensure_facts(con)
            self._built_in_s = round(time.perf_counter() - started, 2)
            self._facts_rows = con.execute(f"SELECT count(*) FROM {FACTS_TABLE}").fetchone()[0]
            self._con = con
        except Exception:
            self._db_lock.release()
            raise

    def _schedule_release(self) -> None:
        self._timer = threading.Timer(self.idle_seconds, self._release_if_idle)
        self._timer.daemon = True
        self._timer.start()

    def _cancel_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _release_if_idle(self) -> None:
        with self._serial:
            if self._con is not None and time.monotonic() - self._last_used >= self.idle_seconds - _IDLE_MARGIN:
                self._close_locked()

    def close(self) -> None:
        """接続を閉じてロックを手放す。何度呼んでもよい。"""
        with self._serial:
            self._cancel_timer()
            self._close_locked()

    def _close_locked(self) -> None:
        if self._con is None:
            return
        self._con.close()
        self._con = None
        self._db_lock.release()

    def state(self) -> dict[str, Any]:
        """画面に見せる状態。"""
        return {
            "open": self._con is not None, "facts_rows": self._facts_rows, "built_in_s": self._built_in_s,
            "idle_seconds": self.idle_seconds, "db": str(self.path),
        }
