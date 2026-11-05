"""今週の予想（tools/今週の予想/forecast.py）を別プロセスで動かす。"""

from __future__ import annotations

import subprocess
import sys
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from 発走前の通知.folders import FORECAST_SCRIPT, LOG_FOLDER, PROJECT
from 発走前の通知.uv_locator import child_env, uv_command

#: 失敗したときに知らせる、記録の最後の行数。
_TAIL_LINES = 5


def _stderr(text: str) -> None:
    print(text, file=sys.stderr, flush=True)


class ForecastRunner:
    """朝はその日の全レース（同じ時点で作ってあるレースは飛ばす。終わったレースの回顧も書き足す）、
    発走前は1レース（回顧は飛ばす）を forecast.py で予想する。forecast.py は予想のあとに、その日の買うレースの計画・
    買い目の記録・まとめも書き直す。forecast.py の出力（表と進み具合）は ``reports/発走前の通知/logs/<開催日>.log`` に足す。
    """

    def __init__(self, *, project: Path = PROJECT, script: Path = FORECAST_SCRIPT, log_folder: Path = LOG_FOLDER,
                 log: Callable[[str], None] = _stderr, run: Callable[..., subprocess.CompletedProcess] = subprocess.run, uv: str | None = None,
                 now: Callable[[], datetime] = datetime.now) -> None:
        self._project = project
        self._script = script
        self._log_folder = log_folder
        self._log = log
        self._run_process = run
        self._uv = uv
        self._now = now

    def run_day(self, day: str) -> None:
        self._run(["--date", day, "--skip-saved"], f"{day} の全レースの予想", day)

    def run_race(self, rid: str, day: str) -> None:
        self._run([rid, "--no-review"], f"{rid} の予想", day)

    def log_path(self, day: str) -> Path:
        return self._log_folder / f"{day}.log"

    def _run(self, arguments: list[str], label: str, day: str) -> None:
        command = [self._uv or uv_command(), "run", "--project", str(self._project), "python", str(self._script), *arguments]
        path = self.log_path(day)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._log(f"{label}を始めます（記録: {path}）")
        started = time.monotonic()
        with path.open("a", encoding="utf-8") as log:
            log.write(f"\n\n# {label}（{self._now():%Y-%m-%d %H:%M}）\n\n")
            log.flush()
            result = self._run_process(command, cwd=self._project, env=child_env(), stdout=log, stderr=subprocess.STDOUT, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"{label}に失敗しました（記録: {path}）:\n{self._tail(path)}")
        self._log(f"{label}が終わりました（{time.monotonic() - started:.0f} 秒）")

    @staticmethod
    def _tail(path: Path) -> str:
        lines = path.read_text(encoding="utf-8", errors="replace").strip().splitlines()
        return "\n".join(lines[-_TAIL_LINES:])
