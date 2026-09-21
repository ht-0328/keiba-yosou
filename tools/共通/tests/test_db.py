"""元DB の開き方の契約: 読み取り専用、ロック付き、無ければ分かる誤り。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import db
from 共通.db_lock import DatabaseLock


def test_resolve_db_prefers_argument_then_env(tmp_path: Path, monkeypatch):
    given = tmp_path / "a.duckdb"
    given.write_bytes(b"")
    from_env = tmp_path / "b.duckdb"
    from_env.write_bytes(b"")
    monkeypatch.setenv(db.DB_ENV, str(from_env))
    assert db.resolve_db(given) == given.resolve()
    assert db.resolve_db(None) == from_env.resolve()


def test_resolve_db_missing_file_says_where_it_looked(tmp_path: Path):
    missing = tmp_path / "none.duckdb"
    with pytest.raises(FileNotFoundError, match="none.duckdb"):
        db.resolve_db(missing)


def test_open_db_reads_but_cannot_write(one_race_db: Path):
    with db.open_db(one_race_db) as con:
        assert con.execute("SELECT count(*) FROM ra").fetchone()[0] == 1
        with pytest.raises(Exception):
            con.execute("CREATE TABLE scratch (a INTEGER)")


def test_open_db_refuses_while_locked(one_race_db: Path):
    other = DatabaseLock(one_race_db)
    assert other.acquire(timeout=1)
    try:
        with pytest.raises(BlockingIOError):
            with db.open_db(one_race_db, lock_timeout=0.2):
                pass
    finally:
        other.release()


def test_open_db_releases_lock_after_use(one_race_db: Path):
    with db.open_db(one_race_db):
        pass
    probe = DatabaseLock(one_race_db)
    assert probe.acquire(timeout=0.2)
    probe.release()
