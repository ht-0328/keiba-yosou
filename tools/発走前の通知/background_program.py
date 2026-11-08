"""keiba-yosou のプログラム（WIN5 の予想など）を、待たずに裏の処理として動かす。"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from typing import IO

from 発走前の通知.folders import LOG_FOLDER, PROJECT
from 発走前の通知.uv_locator import child_env, uv_command

#: 失敗したときに知らせる、記録の最後の行数。
_TAIL_LINES = 5


def _stderr(text: str) -> None:
    print(text, file=sys.stderr, flush=True)


class BackgroundProgram:
    """``program``（``uv run --project <project>`` の後ろ）を ``subprocess.Popen`` で始めて、すぐ戻る。出力はその日の記録
    （``<log_folder>/<log_name><開催日>.log``）に足す。``finished`` で終わったかを確かめ、``kill`` で止める。同時に動かすのは1つだけ。"""

    def __init__(self, *, program: Sequence[str], project: Path = PROJECT, log_folder: Path = LOG_FOLDER, log_name: str = "",
                 popen: Callable[..., subprocess.Popen] = subprocess.Popen, uv: str | None = None,
                 now: Callable[[], datetime] = datetime.now, log: Callable[[str], None] = _stderr) -> None:
        self._program = tuple(program)
        self._project = project
        self._log_folder = log_folder
        self._log_name = log_name
        self._popen = popen
        self._uv = uv
        self._now = now
        self._log = log
        self._process: subprocess.Popen | None = None
        self._output: IO[str] | None = None
        self._day = ""

    def log_path(self, day: str) -> Path:
        return self._log_folder / f"{self._log_name}{day}.log"

    def start(self, arguments: list[str], label: str, day: str) -> None:
        """``program`` に ``arguments`` を付けて裏で始める。"""
        self.kill()
        path = self.log_path(day)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._output = path.open("a", encoding="utf-8")
        self._output.write(f"\n\n# {label}（{self._now():%Y-%m-%d %H:%M}。裏の処理）\n\n")
        self._output.flush()
        command = [self._uv or uv_command(), "run", "--project", str(self._project), *self._program, *arguments]
        self._process = self._popen(command, cwd=self._project, env=child_env(), stdout=self._output, stderr=subprocess.STDOUT)
        self._day = day
        self._log(f"{label}を裏で始めました（記録: {path}）")

    def finished(self) -> bool:
        """裏の処理が終わったか（始めていなければ True）。終わっていれば記録のファイルを閉じる。"""
        if self._process is None or self._process.poll() is None:
            return self._process is None
        self._close()
        return True

    @property
    def returncode(self) -> int | None:
        return None if self._process is None else self._process.returncode

    def tail(self) -> str:
        """記録の最後の数行（失敗の知らせに添える）。"""
        path = self.log_path(self._day)
        lines = path.read_text(encoding="utf-8", errors="replace").strip().splitlines() if path.is_file() else []
        return "\n".join(lines[-_TAIL_LINES:])

    def kill(self) -> None:
        """動いていれば止める。"""
        if self._process is not None and self._process.poll() is None:
            self._process.kill()
            self._process.wait()
        self._close()

    def _close(self) -> None:
        if self._output is not None:
            self._output.close()
            self._output = None
