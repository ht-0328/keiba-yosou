"""jvdata-store の画面と共有する排他規約: ``<DB絶対パス>.ui.lock`` の先頭1バイト。

``../jvdata-store/src/jvstore/web/db_lock.py`` の写し。互いの Python パッケージには依存しない。
ロックファイルは残す。プロセス終了時には OS がロックを解放する。
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path

#: ロックファイルの末尾に付ける名前。
LOCK_SUFFIX = ".ui.lock"


class DatabaseLock:
    """1つの DB に対する、画面・コマンド間の排他。"""

    def __init__(self, db: Path):
        self.path = Path(str(db.resolve()) + LOCK_SUFFIX)
        self.local = threading.Lock()
        self.file = None

    def acquire(self, timeout: float = 60) -> bool:
        """ロックを取る。時間内に取れなければ False。"""
        deadline = time.monotonic() + timeout
        if not self.local.acquire(timeout=max(0, timeout)):
            return False
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.file = self.path.open("a+b")
            if self.path.stat().st_size == 0:
                self.file.write(b"0")
                self.file.flush()
            while True:
                self.file.seek(0)
                try:
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return True
                except OSError:
                    if time.monotonic() >= deadline:
                        self.file.close()
                        self.file = None
                        self.local.release()
                        return False
                    time.sleep(min(0.1, max(0, deadline - time.monotonic())))
        except Exception:
            if self.file is not None:
                self.file.close()
                self.file = None
            self.local.release()
            raise

    def release(self) -> None:
        """ロックを手放す。close が OS のファイルロックも解放する。"""
        self.file.close()
        self.file = None
        self.local.release()

    def __enter__(self) -> "DatabaseLock":
        if not self.acquire():
            raise TimeoutError("データベースを別の画面で使用中です。処理が終わってから再実行してください。")
        return self

    def __exit__(self, *args: object) -> None:
        self.release()
