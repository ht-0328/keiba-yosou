"""StoreFetcher（jvstore を呼ぶ）のテスト。jvstore は動かさず、呼ばれたコマンドを覚える。"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from 発走前の通知.store_fetcher import StoreFetcher


class _Run:
    def __init__(self, returncode: int = 0, output: str = "") -> None:
        self.commands: list[list[str]] = []
        self._returncode = returncode
        self._output = output

    def __call__(self, command, **_) -> subprocess.CompletedProcess:
        self.commands.append(list(command))
        return subprocess.CompletedProcess(command, self._returncode, stdout=self._output, stderr="")


def _fetcher(run: _Run, logs: list[str] | None = None) -> StoreFetcher:
    collected = [] if logs is None else logs
    return StoreFetcher(store_project=Path("store"), db_name="x.duckdb", log=collected.append, run=run, uv="uv")


def test_発走前は開催日単位の速報5種類とそのレースのオッズ() -> None:
    run = _Run()
    _fetcher(run).fetch_race("2025-04-19", "2025041905010101")
    assert [(command[5], command[7], command[9]) for command in run.commands] == [
        ("rt", "0B15", "20250419"), ("rt", "0B14", "20250419"), ("rt", "0B11", "20250419"), ("rt", "0B13", "20250419"),
        ("rt", "0B17", "20250419"), ("rt", "0B30", "2025041905010101"),
    ]
    assert run.commands[0][:4] == ["uv", "run", "--project", "store"]
    assert run.commands[0][-2:] == ["--db", "x.duckdb"]


def test_朝は出馬表とその日の速報() -> None:
    run = _Run()
    logs: list[str] = []
    fetcher = _fetcher(run, logs)
    fetcher.sync()
    fetcher.fetch_day("2025-04-19")
    assert run.commands[0][4:] == ["jvstore", "sync"]
    assert run.commands[1][5:] == ["realtime", "--db", "x.duckdb", "--date", "2025-04-19"]
    assert logs[0].startswith("出馬表の取り込み（jvstore sync）が終わりました")


def test_失敗したら出力の最後を添えて止まる() -> None:
    run = _Run(returncode=1, output="1\n2\n3\n4\n5\nDB を別の画面で使用中です")
    with pytest.raises(RuntimeError, match="速報の取り込み（2025-04-19）に失敗しました:\n2\n3\n4\n5\nDB を別の画面で使用中です"):
        _fetcher(run).fetch_day("2025-04-19")
