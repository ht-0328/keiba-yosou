"""元DB（jvdata-store の DuckDB）を読み取り専用で開く。

取得・取り込みは jvdata-store の責務で、ここでは開いて読むだけ。
開く前に jvdata-store の画面と同じ規約のロック（``<DB>.ui.lock``）を取り、取得中の書き込みと衝突しないようにする。

    from 共通.db import open_db
    with open_db() as con:
        con.execute("select count(*) from ra")
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import Iterator
from pathlib import Path

import duckdb

from .db_lock import DatabaseLock

#: 既定の元DB。keiba-yosou の隣に jvdata-store を置いている前提。
DEFAULT_DB = Path(__file__).resolve().parents[2].parent / "jvdata-store" / "jvdata.duckdb"
#: 既定を変える環境変数。``--db`` があればそちらが勝つ。
DB_ENV = "YOSOU_DB"
#: ロックを待つ上限（秒）。jvdata-store の画面が短い読み出しをしている間は待つ。
LOCK_TIMEOUT_SECONDS = 15.0
#: 接続の設定。読むだけなので、外部ファイルの読み書きと設定の変更を断つ。
CONNECT_CONFIG = {"enable_external_access": "false", "lock_configuration": "true"}


def resolve_db(path: str | Path | None = None) -> Path:
    """DB のパスを決める。``--db`` > 環境変数 > 既定 の順。無ければ ``FileNotFoundError``。"""
    chosen = Path(path) if path else Path(os.environ.get(DB_ENV) or DEFAULT_DB)
    chosen = chosen.expanduser().resolve()
    if not chosen.exists():
        raise FileNotFoundError(
            f"DB が見つかりません: {chosen}\n"
            f"隣の jvdata-store で取得するか、--db か環境変数 {DB_ENV} で場所を指定してください。"
        )
    return chosen


def connect(path: Path) -> duckdb.DuckDBPyConnection:
    """読み取り専用で開く。書き込みや外部ファイルへの出力はできない。"""
    return duckdb.connect(str(path), read_only=True, config=CONNECT_CONFIG)


@contextlib.contextmanager
def open_db(
    path: str | Path | None = None, *, lock_timeout: float = LOCK_TIMEOUT_SECONDS, use_lock: bool = True,
) -> Iterator[duckdb.DuckDBPyConnection]:
    """ロックを取って開き、抜けるときに閉じてロックを手放す。

    取得中（jvdata-store がロックを持っている）なら ``BlockingIOError``。
    ``use_lock=False`` は、呼ぶ側が既にロックを持っているとき（画面のセッション）に使う。
    """
    db = resolve_db(path)
    lock = DatabaseLock(db) if use_lock else None
    if lock is not None and not lock.acquire(timeout=lock_timeout):
        raise BlockingIOError(
            "DB を別の画面（jvdata-store の取得など）で使用中です。終わってから実行してください。"
        )
    try:
        con = connect(db)
        try:
            yield con
        finally:
            con.close()
    finally:
        if lock is not None:
            lock.release()
