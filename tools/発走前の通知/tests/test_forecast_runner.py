"""ForecastRunner（forecast.py を呼ぶ）のテスト。forecast.py は動かさず、呼ばれたコマンドと記録を確かめる。"""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from 発走前の通知.forecast_runner import ForecastRunner


class _Run:
    def __init__(self, returncode: int = 0, output: str = "") -> None:
        self.commands: list[list[str]] = []
        self._returncode = returncode
        self._output = output

    def __call__(self, command, *, stdout, **_) -> subprocess.CompletedProcess:
        self.commands.append(list(command))
        stdout.write(self._output)
        return subprocess.CompletedProcess(command, self._returncode)


def _runner(run: _Run, tmp_path: Path) -> ForecastRunner:
    return ForecastRunner(project=Path("proj"), script=Path("proj/forecast.py"), log_folder=tmp_path, log=lambda _: None, run=run, uv="uv",
                          now=lambda: datetime(2025, 4, 19, 9, 50))


def test_朝は全レースを同じ時点なら飛ばして_発走前は1レースを回顧なしで(tmp_path: Path) -> None:
    run = _Run(output="表\n")
    runner = _runner(run, tmp_path)
    runner.run_day("2025-04-19")
    runner.run_race("2025041905010101", "2025-04-19")
    assert run.commands[0] == ["uv", "run", "--project", "proj", "python", str(Path("proj/forecast.py")), "--date", "2025-04-19", "--skip-saved"]
    assert run.commands[1][6:] == ["2025041905010101", "--no-review"]
    log = (tmp_path / "2025-04-19.log").read_text(encoding="utf-8")
    assert "# 2025-04-19 の全レースの予想（2025-04-19 09:50）" in log
    assert "# 2025041905010101 の予想（2025-04-19 09:50）" in log
    assert log.count("表\n") == 2


def test_計画だけの決め直しは予想と回顧を飛ばす(tmp_path: Path) -> None:
    run = _Run()
    _runner(run, tmp_path).run_plan("2025-04-20")
    assert run.commands[0][6:] == ["--date", "2025-04-20", "--plan-only", "--no-review"]
    assert "# 2025-04-20 の買うレースの計画" in (tmp_path / "2025-04-20.log").read_text(encoding="utf-8")


def test_失敗したら記録の最後を添えて止まる(tmp_path: Path) -> None:
    run = _Run(returncode=1, output="進み具合\nTraceback\nValueError: 馬体重がない\n")
    with pytest.raises(RuntimeError, match=r"(?s)の予想に失敗しました（記録: .*2025-04-19\.log）:\n.*ValueError: 馬体重がない"):
        _runner(run, tmp_path).run_race("2025041905010101", "2025-04-19")


def test_別のプログラムを渡すと_forecast_py_の代わりに動かし_記録の名前に頭を付ける(tmp_path: Path) -> None:
    run = _Run(output="{}\n")
    runner = ForecastRunner(project=Path("proj"), log_folder=tmp_path, log=lambda _: None, run=run, uv="uv",
                            now=lambda: datetime(2026, 11, 5, 10, 15), program=("python", "-m", "yosou.local_form_aptitude_top3", "predict"),
                            log_name="地方-")
    runner.run(["2026110547150401", "--timing", "当日"], "2026110547150401 の予想", "2026-11-05")
    assert run.commands[0] == ["uv", "run", "--project", "proj", "python", "-m", "yosou.local_form_aptitude_top3", "predict",
                               "2026110547150401", "--timing", "当日"]
    assert runner.log_path("2026-11-05") == tmp_path / "地方-2026-11-05.log"
    assert "# 2026110547150401 の予想（2026-11-05 10:15）" in runner.log_path("2026-11-05").read_text(encoding="utf-8")
