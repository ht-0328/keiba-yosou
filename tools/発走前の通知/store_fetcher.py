"""jvdata-store の jvstore（地方は nvdata-store の nvstore）を別プロセスで動かして、出馬表と速報を元DB に入れる。"""

from __future__ import annotations

import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

from 発走前の通知.folders import LOCAL_STORE_DB, LOCAL_STORE_PROJECT, STORE_DB, STORE_PROJECT
from 発走前の通知.uv_locator import child_env, uv_command

#: 発走前に開催日単位で取り直す速報（jvdata-store の realtime と同じ並び）:
#: 出馬表の更新（取消・騎手変更）、天候と馬場状態（発走時刻の変更も）、馬体重、マイニング予想（直前予想）。
DAY_DATASPECS: tuple[str, ...] = ("0B15", "0B14", "0B11", "0B13", "0B17")
#: 発走前にそのレースだけ取り直す速報: 全賭式のオッズ。
RACE_DATASPEC = "0B30"
#: 地方（nvdata-store の realtime と同じ並び。地方競馬DATA にマイニング予想は無い）: 出馬表の更新、天候と馬場状態、馬体重。
LOCAL_DAY_DATASPECS: tuple[str, ...] = ("0B15", "0B14", "0B11")
#: 地方の出馬表の取り込みで取る蓄積系（生産者マスタ DIFF は予想に要らず、取るのに時間がかかるので外す）。
LOCAL_SYNC_ARGUMENTS: tuple[str, ...] = ("--dataspec", "RACE,DIFN,SNAP")
#: 地方（nvdata-store の realtime と同じ並び。地方競馬DATA にマイニング予想は無い）: 出馬表の更新、天候と馬場状態、馬体重。
LOCAL_DAY_DATASPECS: tuple[str, ...] = ("0B15", "0B14", "0B11")
#: 地方の出馬表の取り込みで取る蓄積系（生産者マスタ DIFF は予想に要らず、取るのに時間がかかるので外す）。
LOCAL_SYNC_ARGUMENTS: tuple[str, ...] = ("--dataspec", "RACE,DIFN,SNAP")
#: 失敗したときに知らせる、出力の最後の行数。
_TAIL_LINES = 5


def _stderr(text: str) -> None:
    print(text, file=sys.stderr, flush=True)


class StoreFetcher:
    """取り込みの中身は jvdata-store（地方は nvdata-store）の責務で、ここは jvstore（nvstore）のコマンドを呼ぶだけ（地方は ``local()``）。
    朝は出馬表（``jvstore sync``）とその日の速報（``jvstore realtime``。全レースのオッズまで取るので 20〜30 秒）、
    発走前は開催日単位の速報 5 種類とそのレースのオッズ（``jvstore rt``。合わせて 10 秒ほど）。
    失敗したら、出力の最後の数行を添えて ``RuntimeError``。
    """

    def __init__(self, *, store_project: Path = STORE_PROJECT, db_name: str = STORE_DB,
                 log: Callable[[str], None] = _stderr, run: Callable[..., subprocess.CompletedProcess] = subprocess.run, uv: str | None = None,
                 tool: str = "jvstore", day_dataspecs: tuple[str, ...] = DAY_DATASPECS, sync_arguments: tuple[str, ...] = ()) -> None:
        self._project = store_project
        self._db = db_name
        self._tool = tool
        self._day_dataspecs = day_dataspecs
        self._sync_arguments = sync_arguments
        self._log = log
        self._run_process = run
        self._uv = uv

    @classmethod
    def local(cls, **options) -> StoreFetcher:
        """地方: nvdata-store の nvstore を呼ぶ。開催日単位の速報は 3 種類、出馬表の取り込みは RACE・DIFN・SNAP だけ。"""
        return cls(store_project=LOCAL_STORE_PROJECT, db_name=LOCAL_STORE_DB, tool="nvstore", day_dataspecs=LOCAL_DAY_DATASPECS,
                   sync_arguments=LOCAL_SYNC_ARGUMENTS, **options)

    def sync(self) -> None:
        """今週の出馬表など、蓄積系の差分を取り込む。"""
        self._run(["sync", *self._sync_arguments], f"出馬表の取り込み（{self._tool} sync）")

    def fetch_day(self, day: str) -> None:
        """その日の速報を全部（出馬表の更新・天候馬場・馬体重・マイニング予想・全レースのオッズ）取り込む。"""
        self._run(["realtime", "--db", self._db, "--date", day], f"速報の取り込み（{day}）")

    def fetch_race(self, day: str, rid: str) -> None:
        """発走前に、開催日単位の速報とそのレースのオッズだけを取り直す。"""
        key = day.replace("-", "")
        for dataspec in self._day_dataspecs:
            self._run(["rt", "--dataspec", dataspec, "--key", key, "--db", self._db], f"速報 {dataspec}（{day}）")
        self._run(["rt", "--dataspec", RACE_DATASPEC, "--key", rid, "--db", self._db], f"速報 {RACE_DATASPEC}（{rid}）")

    def _run(self, arguments: list[str], label: str) -> None:
        command = [self._uv or uv_command(), "run", "--project", str(self._project), self._tool, *arguments]
        started = time.monotonic()
        result = self._run_process(command, cwd=self._project, env=child_env(), capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", check=False)
        if result.returncode != 0:
            tail = "\n".join((result.stdout + result.stderr).strip().splitlines()[-_TAIL_LINES:])
            raise RuntimeError(f"{label}に失敗しました:\n{tail}")
        self._log(f"{label}が終わりました（{time.monotonic() - started:.0f} 秒）")
