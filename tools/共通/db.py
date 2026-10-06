"""元DB（jvdata-store か nvdata-store の DuckDB）を読み取り専用で開く。

取得・取り込みは jvdata-store・nvdata-store の責務で、ここでは開いて読むだけ。
開く前に取得の画面と同じ規約のロック（``<DB>.ui.lock``）を取り、取得中の書き込みと衝突しないようにする。

    from 共通.db import open_db
    with open_db() as con:                      # 中央（既定）
        con.execute("select count(*) from ra")
    with open_db(default=LOCAL) as con:         # 地方（nvdata-store）
        ...
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import duckdb

from .db_lock import DatabaseLock

#: keiba-yosou の隣のフォルダ（jvdata-store・nvdata-store を置いている前提）。
_WORKSPACE = Path(__file__).resolve().parents[2].parent


@dataclass(frozen=True)
class DatabaseDefault:
    """元DB の既定（パス・それを変える環境変数・貯める道具の名前）。中央と地方で1つずつある。"""

    path: Path
    env: str
    store: str

    def help(self) -> str:
        """コマンドの ``--db`` の説明。"""
        return f"元DB のパス（既定: ../{self.store}/{self.path.name} か環境変数 {self.env}）"


#: 中央の元DB（jvdata-store）。``--db`` があればそちらが勝つ。
JRA = DatabaseDefault(_WORKSPACE / "jvdata-store" / "jvdata.duckdb", "YOSOU_DB", "jvdata-store")
#: 地方の元DB（nvdata-store）。
LOCAL = DatabaseDefault(_WORKSPACE / "nvdata-store" / "nvdata.duckdb", "YOSOU_LOCAL_DB", "nvdata-store")
#: 中央の既定のパスと環境変数の名前（今までの名前。使っている道具のために残す）。
DEFAULT_DB = JRA.path
DB_ENV = JRA.env
#: ロックを待つ上限（秒）。取得の画面が短い読み出しをしている間は待つ。
LOCK_TIMEOUT_SECONDS = 15.0
#: 接続の設定。読むだけなので、外部ファイルの読み書きと設定の変更を断つ。
CONNECT_CONFIG = {"enable_external_access": "false", "lock_configuration": "true"}


def resolve_db(path: str | Path | None = None, default: DatabaseDefault = JRA) -> Path:
    """DB のパスを決める。``--db`` > 環境変数 > 既定 の順。無ければ ``FileNotFoundError``。"""
    chosen = Path(path) if path else Path(os.environ.get(default.env) or default.path)
    chosen = chosen.expanduser().resolve()
    if not chosen.exists():
        raise FileNotFoundError(
            f"DB が見つかりません: {chosen}\n"
            f"隣の {default.store} で取得するか、--db か環境変数 {default.env} で場所を指定してください。"
        )
    return chosen


def connect(path: Path) -> duckdb.DuckDBPyConnection:
    """読み取り専用で開く。書き込みや外部ファイルへの出力はできない。"""
    return duckdb.connect(str(path), read_only=True, config=CONNECT_CONFIG)


@contextlib.contextmanager
def open_db(
    path: str | Path | None = None, *, lock_timeout: float = LOCK_TIMEOUT_SECONDS, use_lock: bool = True,
    default: DatabaseDefault = JRA,
) -> Iterator[duckdb.DuckDBPyConnection]:
    """ロックを取って開き、抜けるときに閉じてロックを手放す。

    取得中（取得の道具がロックを持っている）なら ``BlockingIOError``。
    ``use_lock=False`` は、呼ぶ側が既にロックを持っているとき（画面のセッション）に使う。
    ``default`` は ``path`` も環境変数も無いときに開く元DB（中央 ``JRA`` か地方 ``LOCAL``）。
    """
    db = resolve_db(path, default)
    lock = DatabaseLock(db) if use_lock else None
    if lock is not None and not lock.acquire(timeout=lock_timeout):
        raise BlockingIOError(
            "DB を別の画面（取得の道具など）で使用中です。終わってから実行してください。"
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
