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


def test_WIN5の前は速報のWIN5と開催日単位の速報と対象レースのオッズ() -> None:
    run = _Run()
    fetcher = _fetcher(run)
    fetcher.fetch_win5("2025-04-20")
    fetcher.fetch_races("2025-04-20", ("2025042005010210", "2025042008010210"))
    assert [(command[5], command[7], command[9]) for command in run.commands] == [
        ("rt", "0B51", "20250420"), ("rt", "0B15", "20250420"), ("rt", "0B14", "20250420"), ("rt", "0B11", "20250420"),
        ("rt", "0B13", "20250420"), ("rt", "0B17", "20250420"), ("rt", "0B30", "2025042005010210"), ("rt", "0B30", "2025042008010210"),
    ]


def test_朝は出馬表とその日の速報と_中央は時系列オッズ() -> None:
    run = _Run()
    logs: list[str] = []
    fetcher = _fetcher(run, logs)
    fetcher.sync()
    fetcher.fetch_day("2025-04-19")
    assert run.commands[0][4:] == ["jvstore", "sync"]
    assert run.commands[1][5:] == ["realtime", "--db", "x.duckdb", "--date", "2025-04-19"]
    assert run.commands[2][5:] == ["timeseries", "--from", "2025-04-19", "--to", "2025-04-19", "--db", "x.duckdb", "--refetch"]
    assert len(run.commands) == 3
    assert logs[0].startswith("出馬表の取り込み（jvstore sync）が終わりました")


def test_失敗したら出力の最後を添えて止まる() -> None:
    run = _Run(returncode=1, output="1\n2\n3\n4\n5\nDB を別の画面で使用中です")
    with pytest.raises(RuntimeError, match="速報の取り込み（2025-04-19）に失敗しました:\n2\n3\n4\n5\nDB を別の画面で使用中です"):
        _fetcher(run).fetch_day("2025-04-19")


class _FailingRun:
    """指定した速報の種類だけ失敗する。"""

    def __init__(self, failing: str) -> None:
        self.commands: list[list[str]] = []
        self._failing = failing

    def __call__(self, command, **_) -> subprocess.CompletedProcess:
        self.commands.append(list(command))
        code = 1 if self._failing in command else 0
        return subprocess.CompletedProcess(command, code, stdout="認証エラー" if code else "", stderr="")


def test_開催日単位の速報が1種類取れなくても_残りとレースのオッズを取って続ける() -> None:
    run = _FailingRun("0B15")
    logs: list[str] = []
    _fetcher(run, logs).fetch_race("2025-04-19", "2025041905010101")
    assert [command[7] for command in run.commands] == ["0B15", "0B14", "0B11", "0B13", "0B17", "0B30"]
    assert any(line.startswith("速報 0B15 を取れませんでした（前に取り込んだ分で続けます）") and "認証エラー" in line for line in logs)


def test_レースのオッズが取れないときは止まる() -> None:
    with pytest.raises(RuntimeError, match="速報 0B30（2025041905010101）に失敗しました"):
        _fetcher(_FailingRun("0B30")).fetch_race("2025-04-19", "2025041905010101")


class _LocalRun:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def __call__(self, command, **_) -> subprocess.CompletedProcess:
        self.commands.append(list(command))
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")


def test_地方は_nvstore_を呼び_出馬表は3種類だけ_速報は馬体重までの3種類とそのレースのオッズ() -> None:
    run = _LocalRun()
    fetcher = StoreFetcher.local(run=run, uv="uv", log=lambda _: None)
    fetcher.sync()
    fetcher.fetch_day("2026-11-05")
    fetcher.fetch_race("2026-11-05", "2026110547150401")
    assert run.commands[0][3].endswith("nvdata-store")
    assert run.commands[0][4:] == ["nvstore", "sync", "--dataspec", "RACE,DIFN,SNAP"]
    assert run.commands[1][4:] == ["nvstore", "realtime", "--db", "nvdata.duckdb", "--date", "2026-11-05"]
    assert [command[7] for command in run.commands[2:5]] == ["0B15", "0B14", "0B11"]
    assert run.commands[5][4:] == ["nvstore", "rt", "--dataspec", "0B30", "--key", "2026110547150401", "--db", "nvdata.duckdb"]
    assert len(run.commands) == 6


def test_地方は_置き場所を渡すと_そのレースの時系列オッズを別の_DB_に取る(tmp_path: Path) -> None:
    run = _LocalRun()
    fetcher = StoreFetcher.local(run=run, uv="uv", log=lambda _: None, history=lambda rid: tmp_path / rid[:8] / "時系列オッズ.duckdb")
    fetcher.fetch_race("2026-11-05", "2026110547150401")
    assert run.commands[-2][4:] == ["nvstore", "rt", "--dataspec", "0B30", "--key", "2026110547150401", "--db", "nvdata.duckdb"]
    assert run.commands[-1][4:] == ["nvstore", "rt", "--dataspec", "0B41", "--key", "202611054701",
                                    "--db", str(tmp_path / "20261105" / "時系列オッズ.duckdb")]
    assert (tmp_path / "20261105").is_dir()


def test_時系列オッズが取れなくても_止めずに知らせる(tmp_path: Path) -> None:
    logs: list[str] = []

    def run(command, **_) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(command, 1 if "0B41" in command else 0, stdout="該当データなし", stderr="")

    fetcher = StoreFetcher.local(run=run, uv="uv", log=logs.append, history=lambda rid: tmp_path / "時系列オッズ.duckdb")
    fetcher.fetch_race("2026-11-05", "2026110547150401")
    assert any("時系列オッズを取れませんでした" in line and "該当データなし" in line for line in logs)
