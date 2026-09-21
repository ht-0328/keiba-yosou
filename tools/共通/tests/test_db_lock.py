"""ロックの契約: 二重に取れない、手放せば取れる。"""

from __future__ import annotations

from pathlib import Path

from 共通.db_lock import DatabaseLock, LOCK_SUFFIX


def test_lock_file_is_beside_db(tmp_path: Path):
    db = tmp_path / "x.duckdb"
    assert DatabaseLock(db).path == Path(str(db.resolve()) + LOCK_SUFFIX)


def test_second_lock_waits_and_fails_until_released(tmp_path: Path):
    db = tmp_path / "x.duckdb"
    first, second = DatabaseLock(db), DatabaseLock(db)
    assert first.acquire(timeout=1)
    assert not second.acquire(timeout=0.2)
    first.release()
    assert second.acquire(timeout=1)
    second.release()


def test_context_manager_releases_on_exit(tmp_path: Path):
    db = tmp_path / "x.duckdb"
    with DatabaseLock(db):
        assert not DatabaseLock(db).acquire(timeout=0.1)
    assert DatabaseLock(db).acquire(timeout=0.1)
